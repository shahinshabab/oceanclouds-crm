# messaging/forms.py
from django import forms

from crm.forms import BootstrapModelForm  # reuse your base form
from .models import MessageTemplate, Campaign, EmailIntegration

class MessageTemplateForm(BootstrapModelForm):
    class Meta:
        model = MessageTemplate
        fields = [
            "name",
            "code",
            "channel",
            "usage",
            "subject",
            "body_text",
            "body_html",
            "description",
            "is_active",
        ]
        widgets = {
            "body_text": forms.Textarea(attrs={"rows": 3}),
            "body_html": forms.Textarea(attrs={"rows": 6}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class CampaignForm(BootstrapModelForm):
    class Meta:
        model = Campaign
        fields = [
            "name",
            "template",
            "integration",
            "subject_override",
            "segment_description",
            "scheduled_for",
        ]
        widgets = {
            "segment_description": forms.Textarea(attrs={"rows": 2}),
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }




class EmailIntegrationForm(BootstrapModelForm):
    class Meta:
        model = EmailIntegration
        fields = [
            "name",
            "backend_type",
            "channel",
            "host",
            "port",
            "username",
            "password",
            "use_tls",
            "use_ssl",
            "from_email",
            "is_default",
        ]
        widgets = {
            "password": forms.PasswordInput(render_value=True),
        }
