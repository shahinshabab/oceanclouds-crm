# sales/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import (
    Deal,
    Proposal,
    ProposalItem,
    Contract,
    Invoice,
    Payment,
)


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
class ProposalForm(BootstrapModelForm):
    class Meta:
        model = Proposal
        fields = [
            "deal",
            "title",
            "version",
            "status",
            "valid_until",
            "subtotal",
            "discount",
            "tax",    # kept visible for now
            "total",
            "notes",
        ]
        widgets = {
            "valid_until": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ProposalItemForm(BootstrapModelForm):
    class Meta:
        model = ProposalItem
        fields = ["service", "package", "description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Description"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01"}),
        }

    def clean(self):
        cleaned = super().clean()
        service = cleaned.get("service")
        package = cleaned.get("package")

        if not service and not package:
            raise forms.ValidationError("Please select a Service or a Package.")
        if service and package:
            raise forms.ValidationError("Select either Service OR Package, not both.")

        return cleaned


ProposalItemFormSet = inlineformset_factory(
    Proposal,
    ProposalItem,
    form=ProposalItemForm,
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
            "number",
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
            "number",
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
