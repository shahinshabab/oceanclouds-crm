from django import forms

from .models import Client, Contact, Lead, Inquiry, ClientReview
from django.contrib.auth import get_user_model

from common.roles import ROLE_MANAGER

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


class ClientForm(BootstrapModelForm):
    class Meta:
        model = Client
        fields = [
            "name",
            "display_name",
            "email",
            "phone",
            "instagram_handle",
            "billing_address",
            "city",
            "district",
            "state",
            "country",
            "notes",
            "is_active",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
            "billing_address": forms.Textarea(attrs={"rows": 2}),
        }


class ContactForm(BootstrapModelForm):
    class Meta:
        model = Contact
        fields = [
            "client",
            "first_name",
            "last_name",
            "role",
            "email",
            "phone",
            "whatsapp",
            "is_primary",
            "allow_marketing",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class LeadForm(BootstrapModelForm):
    class Meta:
        model = Lead
        fields = [
            "name",
            "email",
            "phone",
            "whatsapp",
            "wedding_date",
            "wedding_city",
            "wedding_district",
            "wedding_state",
            "wedding_country",
            "budget_min",
            "budget_max",
            "status",
            "source",         # choice field (website, instagram, etc.)
            "source_detail",  # extra info (referrer name, campaign, etc.)
            "notes",
            "next_action_date",
            "next_action_note",
            "client",
        ]
        widgets = {
            "wedding_date": forms.DateInput(attrs={"type": "date"}),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "next_action_note": forms.TextInput(),
            "source_detail": forms.TextInput(
                attrs={
                    "placeholder": "Eg. Referred by Anita, Instagram campaign name, Expo title…"
                }
            ),
        }
class InquiryForm(BootstrapModelForm):
    class Meta:
        model = Inquiry
        fields = [
            "channel",
            "status",
            "name",
            "email",
            "phone",
            "wedding_date",
            "wedding_city",
            "wedding_district",
            "wedding_state",
            "wedding_country",
            "message",
            "lead",
            "client",
            "handled_by",
        ]
        widgets = {
            "wedding_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        # Queryset = all active managers
        managers_qs = User.objects.filter(
            groups__name=ROLE_MANAGER,
            is_active=True,
        ).order_by("first_name", "last_name", "id")

        self.fields["handled_by"].queryset = managers_qs
        self.fields["handled_by"].label = "Assigned manager"
        self.fields["handled_by"].empty_label = None  # remove "---------" option

        # For NEW inquiries: default to first manager
        if not self.instance.pk and managers_qs.exists():
            if not (self.initial.get("handled_by") or self.instance.handled_by_id):
                self.initial["handled_by"] = managers_qs.first().pk

class ClientReviewForm(BootstrapModelForm):
    class Meta:
        model = ClientReview
        fields = [
            "client",
            "rating",
            "title",
            "comment",
            "next_action",
            "next_action_date",
        ]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
            "next_action": forms.TextInput(attrs={"placeholder": "e.g., Follow-up call, request testimonial"}),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
            "rating": forms.Select(choices=[(i, str(i)) for i in range(1, 6)]),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is not None and not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return rating
