# services/forms.py
from django import forms
from django.forms import inlineformset_factory

from .models import Vendor, Service, Package, PackageItem, InventoryItem


class BootstrapModelForm(forms.ModelForm):
    """
    Base form to automatically add Bootstrap classes to widgets.
    - Text / number / email / URL / textarea / date => form-control
    - Select / ModelChoiceField / ModelMultipleChoiceField => form-select
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

            # Selects (ChoiceField, ModelChoiceField, Multiple select, etc.)
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing_classes + " form-select").strip()

            # Everything else → form-control
            else:
                widget.attrs["class"] = (existing_classes + " form-control").strip()


class VendorForm(BootstrapModelForm):
    class Meta:
        model = Vendor
        fields = [
            "name",
            "company_name",
            "vendor_type",
            "email",
            "phone",
            "alt_phone",
            "whatsapp",
            "address_line1",
            "address_line2",
            "city",
            "district",
            "state",
            "country",
            "is_preferred",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "address_line1": forms.TextInput(attrs={"placeholder": "Street / Building"}),
            "address_line2": forms.TextInput(attrs={"placeholder": "Area / Landmark"}),
        }


class ServiceForm(BootstrapModelForm):
    class Meta:
        model = Service
        fields = [
            "name",
            "code",
            "category",
            "description",
            "base_price",
            "vendors",
            "is_active",
            "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PackageForm(BootstrapModelForm):
    class Meta:
        model = Package
        # total_price is auto-calculated, so we don't expose it directly
        fields = [
            "name",
            "code",
            "description",
            "is_active",
            "notes",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class PackageItemForm(BootstrapModelForm):
    class Meta:
        model = PackageItem
        fields = ["service", "description", "quantity", "unit_price"]
        widgets = {
            "description": forms.TextInput(attrs={"placeholder": "Description"}),
            "quantity": forms.NumberInput(attrs={"min": 1}),
            "unit_price": forms.NumberInput(attrs={"step": "0.01"}),
        }


PackageItemFormSet = inlineformset_factory(
    Package,
    PackageItem,
    form=PackageItemForm,
    extra=1,
    can_delete=True,
)


class InventoryItemForm(BootstrapModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "name",
            "sku",
            "service",
            "quantity_total",
            "quantity_available",
            "unit",
            "location",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
