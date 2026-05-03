# sales/forms.py

from django import forms
from django.forms import inlineformset_factory
from django.forms.models import BaseInlineFormSet

from common.forms import BootstrapModelForm
from services.models import Service, Package

from .models import (
    Deal,
    Proposal,
    ProposalItem,
    Contract,
    Invoice,
    Payment,
)


class DateInput(forms.DateInput):
    input_type = "date"


# ---------------------------------------------------------
# Catalog choices helper
# ---------------------------------------------------------
def get_catalog_choices():
    service_choices = [
        (f"S:{service.id}", f"Service — {service.name}")
        for service in Service.objects.only("id", "name").order_by("name")
    ]

    package_choices = [
        (f"P:{package.id}", f"Package — {package.name}")
        for package in Package.objects.only("id", "name").order_by("name")
    ]

    return [("", "Select item...")] + service_choices + package_choices


# ---------------------------------------------------------
# Deal
# ---------------------------------------------------------
class DealForm(BootstrapModelForm):
    class Meta:
        model = Deal
        fields = [
            "name",
            "client",
            "lead",
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
# Proposal
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
            "discount",
            "tax",
            "notes",
        ]
        widgets = {
            "valid_until": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["discount"].label = "Discount Amount"
        self.fields["discount"].help_text = "Enter fixed discount amount."

        self.fields["tax"].label = "Tax %"
        self.fields["tax"].help_text = "Enter tax percentage, for example 18 for 18%."

        self.fields["discount"].widget.attrs["step"] = "0.01"
        self.fields["tax"].widget.attrs["step"] = "0.01"
        self.fields["tax"].widget.attrs["placeholder"] = "Eg. 18"


# ---------------------------------------------------------
# Proposal Item
# ---------------------------------------------------------
class ProposalItemForm(BootstrapModelForm):
    catalog_item = forms.ChoiceField(
        choices=[],
        required=False,
        label="Item",
        widget=forms.Select(attrs={"class": "catalog-item"}),
    )

    class Meta:
        model = ProposalItem
        fields = [
            "catalog_item",
            "description",
            "quantity",
            "unit_price",
        ]

    def __init__(self, *args, **kwargs):
        catalog_choices = kwargs.pop("catalog_choices", None)
        super().__init__(*args, **kwargs)

        self.fields["catalog_item"].choices = catalog_choices or get_catalog_choices()

        if self.instance and self.instance.pk:
            if self.instance.service_id:
                self.initial["catalog_item"] = f"S:{self.instance.service_id}"
            elif self.instance.package_id:
                self.initial["catalog_item"] = f"P:{self.instance.package_id}"

    def clean(self):
        cleaned_data = super().clean()
        catalog_item = (cleaned_data.get("catalog_item") or "").strip()

        if not catalog_item:
            raise forms.ValidationError("Please select a Service or Package.")

        try:
            item_type, item_id = catalog_item.split(":")
            item_id = int(item_id)
        except ValueError:
            raise forms.ValidationError("Invalid item selected.")

        self.instance.service = None
        self.instance.package = None

        if item_type == "S":
            service = Service.objects.filter(id=item_id).first()

            if not service:
                raise forms.ValidationError("Selected service does not exist.")

            self.instance.service = service

            if service.name.strip().lower() == "other":
                description = (cleaned_data.get("description") or "").strip()
                unit_price = cleaned_data.get("unit_price")

                if not description:
                    self.add_error(
                        "description",
                        "Please enter a description for 'Other'.",
                    )

                if unit_price is None or unit_price <= 0:
                    self.add_error(
                        "unit_price",
                        "Please enter a price for 'Other' item.",
                    )

        elif item_type == "P":
            package = Package.objects.filter(id=item_id).first()

            if not package:
                raise forms.ValidationError("Selected package does not exist.")

            self.instance.package = package

        else:
            raise forms.ValidationError("Invalid item type selected.")

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        catalog_item = self.cleaned_data.get("catalog_item") or ""
        item_type, item_id = catalog_item.split(":")
        item_id = int(item_id)

        instance.service = None
        instance.package = None

        if item_type == "S":
            instance.service_id = item_id
        elif item_type == "P":
            instance.package_id = item_id

        if commit:
            instance.save()

        return instance


class BaseProposalItemFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        self.catalog_choices = kwargs.pop("catalog_choices", get_catalog_choices())
        super().__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs["catalog_choices"] = self.catalog_choices
        return super()._construct_form(i, **kwargs)


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
            "contract",
            "issue_date",
            "due_date",
            "status",
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
            "received_by",
        ]
        widgets = {
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["amount"].widget.attrs["step"] = "0.01"

        invoice_obj = None

        initial_invoice_id = self.initial.get("invoice")
        data_invoice_id = self.data.get("invoice") if self.is_bound else None
        invoice_id = data_invoice_id or initial_invoice_id

        if invoice_id:
            try:
                invoice_obj = Invoice.objects.get(pk=invoice_id)
            except Invoice.DoesNotExist:
                invoice_obj = None

        if invoice_obj:
            remaining = invoice_obj.balance
            self.fields["amount"].widget.attrs["max"] = remaining
            self.fields["amount"].help_text = f"Remaining balance: {remaining}"