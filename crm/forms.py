from django import forms
from django.contrib.auth import get_user_model

from .models import Client, Contact, Lead, Inquiry, ClientReview
from common.roles import ROLE_MANAGER


class BootstrapModelForm(forms.ModelForm):
    """
    Automatically adds Bootstrap classes to Django form fields.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget
            existing_classes = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                bootstrap_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                bootstrap_class = "form-select"
            else:
                bootstrap_class = "form-control"

            widget.attrs["class"] = f"{existing_classes} {bootstrap_class}".strip()


class ClientForm(BootstrapModelForm):
    class Meta:
        model = Client
        fields = [
            "name",
            "display_name",
            "email",
            "phone",
            "billing_address",
            "city",
            "district",
            "state",
            "country",
            "notes",
            "is_active",
        ]
        widgets = {
            "billing_address": forms.Textarea(attrs={"rows": 2}),
            "notes": forms.Textarea(attrs={"rows": 3}),
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
        ]


class InquiryForm(BootstrapModelForm):
    class Meta:
        model = Inquiry
        fields = [
            "channel",
            "status",
            "name",
            "email",
            "phone",
            "whatsapp",
            "message",
            "lead",
            "client",
            "handled_by",
        ]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        User = get_user_model()

        managers_qs = User.objects.filter(
            groups__name=ROLE_MANAGER,
            is_active=True,
        ).order_by("first_name", "last_name", "id")

        self.fields["handled_by"].queryset = managers_qs
        self.fields["handled_by"].label = "Assigned manager"
        self.fields["handled_by"].empty_label = "Select manager"

        if not self.instance.pk and managers_qs.exists():
            if not self.initial.get("handled_by") and not self.instance.handled_by_id:
                self.initial["handled_by"] = managers_qs.first().pk


class LeadForm(BootstrapModelForm):
    class Meta:
        model = Lead
        fields = [
            "inquiry",
            "client",
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
            "source",
            "source_detail",
            "notes",
            "next_action_date",
            "next_action_note",
        ]
        widgets = {
            "wedding_date": forms.DateInput(attrs={"type": "date"}),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "source_detail": forms.TextInput(
                attrs={
                    "placeholder": "Eg. Referred by Anita, Instagram campaign name, Expo title"
                }
            ),
            "next_action_note": forms.TextInput(
                attrs={
                    "placeholder": "Eg. Call client tomorrow, send package details"
                }
            ),
        }


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
            "rating": forms.Select(choices=[("", "Select rating")] + [(i, str(i)) for i in range(1, 6)]),
            "comment": forms.Textarea(attrs={"rows": 4}),
            "next_action": forms.TextInput(
                attrs={"placeholder": "Eg. Follow-up call, request testimonial"}
            ),
            "next_action_date": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")

        if rating is not None and not (1 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 1 and 5.")

        return rating