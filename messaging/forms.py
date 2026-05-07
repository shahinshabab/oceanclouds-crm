# messaging/forms.py

from django import forms
from django.core.exceptions import ValidationError

from common.forms import BootstrapModelForm
from .models import EmailTemplate, EmailTemplateAttachment, Campaign, WhatsAppTemplate, Ticket


class EmailTemplateForm(BootstrapModelForm):
    class Meta:
        model = EmailTemplate
        fields = [
            "name",
            "slug",
            "type",
            "subject",
            "body_html",
            "body_text",
            "is_active",
            "attach_generated_pdf",
            "pdf_attachment_mode",
        ]
        widgets = {
            "body_html": forms.Textarea(attrs={"rows": 14}),
            "body_text": forms.Textarea(attrs={"rows": 6}),
        }

    def clean(self):
        cleaned = super().clean()

        is_active = cleaned.get("is_active")
        template_type = cleaned.get("type")

        if is_active and template_type:
            qs = EmailTemplate.objects.filter(
                type=template_type,
                is_active=True,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError(
                    f"There is already an active template for {template_type}. "
                    "Deactivate the existing template first, or this form will replace it in the view."
                )

        return cleaned


class EmailTemplateAttachmentForm(BootstrapModelForm):
    class Meta:
        model = EmailTemplateAttachment
        fields = ["file", "display_name", "is_active"]


class CampaignForm(BootstrapModelForm):
    class Meta:
        model = Campaign
        fields = [
            "name",
            "template",
            "target_type",
            "description",
            "from_email",
            "reply_to",
            "status",
            "start_date",
            "start_time",
            "weekdays_only",
            "daily_limit",
            "delay_seconds",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["template"].queryset = EmailTemplate.objects.filter(
            type=EmailTemplate.TemplateType.CAMPAIGN,
            is_active=True,
        )

        self.fields["from_email"].required = False
        self.fields["reply_to"].required = False

    def clean_from_email(self):
        return (self.cleaned_data.get("from_email") or "").strip()

    def clean_reply_to(self):
        return (self.cleaned_data.get("reply_to") or "").strip()

    def clean(self):
        cleaned = super().clean()

        status = cleaned.get("status")
        start_date = cleaned.get("start_date")
        start_time = cleaned.get("start_time")

        if status in {Campaign.Status.SCHEDULED, Campaign.Status.RUNNING}:
            if not start_date:
                self.add_error("start_date", "Start date is required for scheduled/running campaigns.")
            if not start_time:
                self.add_error("start_time", "Start time is required for scheduled/running campaigns.")

        return cleaned
    
class WhatsAppTemplateForm(BootstrapModelForm):
    variable_order_raw = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=(
            "One variable per line, in the same order as your WhatsApp template placeholders. "
            "Example:\nevent.name\nevent.date\nvenue.name"
        ),
    )

    class Meta:
        model = WhatsAppTemplate
        fields = [
            "name",
            "slug",
            "type",
            "provider",
            "provider_template_name",
            "language_code",
            "category",
            "header_text",
            "body_text",
            "footer_text",
            "is_active",
            "notes",
        ]
        widgets = {
            "body_text": forms.Textarea(attrs={"rows": 8}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.variable_order:
            self.fields["variable_order_raw"].initial = "\n".join(
                self.instance.variable_order
            )

    def clean_variable_order_raw(self):
        raw = self.cleaned_data.get("variable_order_raw") or ""
        values = []

        for line in raw.splitlines():
            item = line.strip()
            if item:
                values.append(item)

        return values

    def clean(self):
        cleaned = super().clean()

        is_active = cleaned.get("is_active")
        template_type = cleaned.get("type")
        provider = cleaned.get("provider")
        language_code = cleaned.get("language_code")

        if is_active and template_type and provider and language_code:
            qs = WhatsAppTemplate.objects.filter(
                type=template_type,
                provider=provider,
                language_code=language_code,
                is_active=True,
                is_default_for_type=True,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise ValidationError(
                    "There is already an active WhatsApp template for this type, provider, and language."
                )

        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.variable_order = self.cleaned_data.get("variable_order_raw") or []

        if commit:
            instance.save()
            self.save_m2m()

        return instance
    


# -------------------------------------------------------------------
# Support Ticket Form
# -------------------------------------------------------------------

class TicketForm(BootstrapModelForm):
    class Meta:
        model = Ticket
        fields = [
            "category",
            "subject_type",
            "subject",
            "description",
            "priority",
            "screenshot",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            # screenshot uses default ClearableFileInput
        }
