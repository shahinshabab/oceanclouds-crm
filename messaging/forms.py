# messaging/forms.py
from django import forms

from common.forms import BootstrapModelForm  # 🔁 adjust path if needed
from .models import EmailTemplate, Campaign


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
            "is_default_for_type",
        ]
        widgets = {
            # BootstrapModelForm will add classes; we only control type/rows here
            "body_html": forms.Textarea(attrs={"rows": 12}),
            "body_text": forms.Textarea(attrs={"rows": 6}),
        }

class CampaignForm(BootstrapModelForm):
    class Meta:
        model = Campaign
        fields = [
            "name", "template", "target_type",
            "custom_list_raw",
            "description",
            "from_email", "reply_to", "status",
            "start_date", "start_time", "weekdays_only",
            "daily_limit", "delay_seconds",
        ]
        widgets = {
            "custom_list_raw": forms.Textarea(attrs={"rows": 6}),
            "description": forms.Textarea(attrs={"rows": 3}),

            # ✅ HTML5 pickers
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean_from_email(self):
        from_email = self.cleaned_data.get("from_email") or ""
        return from_email.strip()

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        start_date = cleaned.get("start_date")
        start_time = cleaned.get("start_time")

        if status in {"scheduled", "running"}:
            if not start_date:
                self.add_error("start_date", "Start date is required when campaign is scheduled or running.")
            if not start_time:
                self.add_error("start_time", "Start time is required when campaign is scheduled or running.")

        return cleaned
