# sales/forms.py
from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet

from .models import (
    Deal,
    Proposal,
    ProposalItem,
    Contract,
    Invoice,
    Payment,
)
from services.models import Service, Package

class BootstrapModelForm(forms.ModelForm):
    """
    Base form to automatically add Bootstrap classes to widgets.
    - Text / number / email / URL / textarea / date => form-control
    - Select / ModelChoiceField => form-select
    - Checkbox => form-check-input
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            # Keep any existing classes
            existing_classes = widget.attrs.get("class", "")

            # Checkbox
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing_classes + " form-check-input").strip()

            # Selects (ChoiceField, ModelChoiceField, etc.)
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing_classes + " form-select").strip()

            # Everything else → form-control
            else:
                widget.attrs["class"] = (existing_classes + " form-control").strip()

class BaseProposalItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.catalog_choices = kwargs.pop("catalog_choices", get_catalog_choices())
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["catalog_choices"] = self.catalog_choices
        return super()._construct_form(i, **kwargs)
    
class DateInput(forms.DateInput):
    input_type = "date"


# ---------------------------------------------------------
# Deal
# ---------------------------------------------------------
class DealForm(BootstrapModelForm):
    class Meta:
        model = Deal
        fields = [
            "name",
            "client",
            "stage",
            "amount",
            "expected_close_date",
            "description",
            "is_active",
            "closed_on",
        ]
        widgets = {
            "expected_close_date": DateInput(),
            "closed_on": DateInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


# ---------------------------------------------------------
# Proposal + ProposalItem
# ---------------------------------------------------------
def get_catalog_choices():
    service_choices = [(f"S:{s.id}", f"Service — {s.name}") for s in Service.objects.all().order_by("name")]
    package_choices = [(f"P:{p.id}", f"Package — {p.name}") for p in Package.objects.all().order_by("name")]
    return [("", "Select item...")] + service_choices + package_choices

class ProposalForm(BootstrapModelForm):
    class Meta:
        model = Proposal
        fields = [
            "deal",
            "title",
            "version",
            "status",
            "valid_until",
            "discount",
            "tax",
            "notes",
        ]
        widgets = {
            "valid_until": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ProposalItemForm(BootstrapModelForm):
    catalog_item = forms.ChoiceField(
        choices=[],
        required=False,
        widget=forms.Select(attrs={"class": "form-select catalog-item"}),
        label="Item",
    )

    class Meta:
        model = ProposalItem
        fields = ["catalog_item", "description", "quantity", "unit_price"]

    def __init__(self, *args, **kwargs):
        catalog_choices = kwargs.pop("catalog_choices", None)
        super().__init__(*args, **kwargs)

        self.fields["catalog_item"].choices = catalog_choices or get_catalog_choices()

        # set initial for edit
        if self.instance and self.instance.pk:
            if self.instance.service_id:
                self.initial["catalog_item"] = f"S:{self.instance.service_id}"
            elif self.instance.package_id:
                self.initial["catalog_item"] = f"P:{self.instance.package_id}"


    def clean(self):
        cleaned = super().clean()
        key = (cleaned.get("catalog_item") or "").strip()

        if not key:
            raise forms.ValidationError("Please select a Service or a Package.")

        try:
            kind, raw_id = key.split(":")
            obj_id = int(raw_id)
        except Exception:
            raise forms.ValidationError("Invalid item selected.")

        # ✅ set on instance (important)
        self.instance.service = None
        self.instance.package = None

        if kind == "S":
            service = Service.objects.filter(id=obj_id).first()
            if not service:
                raise forms.ValidationError("Selected service does not exist.")
            self.instance.service = service

        elif kind == "P":
            package = Package.objects.filter(id=obj_id).first()
            if not package:
                raise forms.ValidationError("Selected package does not exist.")
            self.instance.package = package
        else:
            raise forms.ValidationError("Invalid item type selected.")

        # Other handling
        desc = (cleaned.get("description") or "").strip()
        unit = cleaned.get("unit_price")

        if self.instance.service and self.instance.service.name.strip().lower() == "other":
            if not desc:
                self.add_error("description", "Please enter a description for 'Other'.")
            if unit is None or unit <= 0:
                self.add_error("unit_price", "Please enter a price for 'Other' item.")

        return cleaned


    def save(self, commit=True):
        inst = super().save(commit=False)
        key = self.cleaned_data.get("catalog_item") or ""
        kind, raw_id = key.split(":")
        obj_id = int(raw_id)

        # Enforce identity: one of them only
        inst.service = None
        inst.package = None

        if kind == "S":
            inst.service_id = obj_id
        else:
            inst.package_id = obj_id

        if commit:
            inst.save()
        return inst


ProposalItemFormSet = inlineformset_factory(
    Proposal,
    ProposalItem,
    form=ProposalItemForm,
    formset=BaseProposalItemFormSet,
    extra=1,
    can_delete=True,
)


# ---------------------------------------------------------
# Contract
# ---------------------------------------------------------
class ContractForm(BootstrapModelForm):
    class Meta:
        model = Contract
        fields = [
            "deal",
            "proposal",
            "status",
            "signed_date",
            "start_date",
            "end_date",
            "terms",
            "file",
        ]
        widgets = {
            "signed_date": DateInput(),
            "start_date": DateInput(),
            "end_date": DateInput(),
            "terms": forms.Textarea(attrs={"rows": 4}),
        }


# ---------------------------------------------------------
# Invoice
# ---------------------------------------------------------
class InvoiceForm(BootstrapModelForm):
    class Meta:
        model = Invoice
        fields = [
            "deal",
            "issue_date",
            "due_date",
            "status",
            "subtotal",
            "tax",          # default 0 in model for now
            "total",
            "notes",
        ]
        widgets = {
            "issue_date": DateInput(),
            "due_date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


# ---------------------------------------------------------
# Payment
# ---------------------------------------------------------
class PaymentForm(BootstrapModelForm):
    class Meta:
        model = Payment
        fields = [
            "invoice",
            "date",
            "amount",
            "payment_type",
            "method",
            "reference",
            "notes",
        ]
        widgets = {
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Optional UX: set a max attribute on amount based on selected invoice
        invoice_obj = None

        # 1) If coming from ?invoice=123 in URL, view will set initial
        initial_invoice_id = self.initial.get("invoice")

        # 2) If bound form, get invoice from POST data
        data_invoice_id = self.data.get("invoice") if self.is_bound else None

        invoice_id = data_invoice_id or initial_invoice_id

        from .models import Invoice  # local import to avoid circular issues

        if invoice_id:
            try:
                invoice_obj = Invoice.objects.get(pk=invoice_id)
            except Invoice.DoesNotExist:
                invoice_obj = None

        if invoice_obj:
            remaining = invoice_obj.balance  # uses @property on Invoice
            # Just UI hint; real enforcement is in Payment.clean()
            self.fields["amount"].widget.attrs["max"] = remaining
