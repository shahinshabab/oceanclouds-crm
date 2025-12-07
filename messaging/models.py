# messaging/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from events.models import EventPerson  # add this import
from crm.models import Client, Contact  # adjust if your actual paths differ

class Channel(models.TextChoices):
    EMAIL = "email", "Email"
    WHATSAPP = "whatsapp", "WhatsApp"
    SMS = "sms", "SMS"


class EmailIntegration(models.Model):
    """
    Stores SMTP/API details so you can manage them from a UI page.
    You can have multiple configs, and mark one as default.
    """
    name = models.CharField(max_length=100, unique=True)
    is_default = models.BooleanField(default=False)

    # generic channel
    channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.EMAIL
    )

    # Basic SMTP fields (works with Django's EmailBackend)
    host = models.CharField(max_length=255, blank=True)
    port = models.PositiveIntegerField(default=587)
    username = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    use_tls = models.BooleanField(default=True)
    use_ssl = models.BooleanField(default=False)
    from_email = models.EmailField(blank=True)

    # For API providers (SendGrid, Mailgun, etc.) – optional
    backend_type = models.CharField(
        max_length=50,
        choices=(
            ("smtp", "SMTP (Django EmailBackend)"),
            ("sendgrid", "SendGrid"),
            ("mailgun", "Mailgun"),
        ),
        default="smtp",
    )
    api_key = models.CharField(max_length=255, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Integration"
        verbose_name_plural = "Email Integrations"

    def __str__(self):
        return f"{self.name} ({self.get_backend_type_display()})"

    @classmethod
    def get_default(cls):
        return cls.objects.filter(is_default=True).first()


class TemplateUsage(models.TextChoices):
    GENERIC = "generic", "Generic / Campaign"
    CONTRACT = "contract", "Contract Email"
    PROPOSAL = "proposal", "Proposal Email"
    ANNIVERSARY = "anniversary", "Anniversary Email (Event Person)"
    REMINDER = "reminder", "Reminder / Follow-up"


class MessageTemplate(models.Model):
    """
    Stores email/SMS/WhatsApp templates in DB.

    You can have:
      - Contract templates
      - Proposal templates
      - Anniversary templates for EventPerson
      - Generic campaign offers
    """
    name = models.CharField(max_length=150)
    code = models.SlugField(
        max_length=100,
        unique=True,
        help_text="Stable identifier (e.g. 'proposal_default', 'anniversary_basic')",
    )
    channel = models.CharField(
        max_length=20, choices=Channel.choices, default=Channel.EMAIL
    )
    usage = models.CharField(
        max_length=50,
        choices=TemplateUsage.choices,
        default=TemplateUsage.GENERIC,
    )

    subject = models.CharField(max_length=255, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(
        blank=True,
        help_text="You can use Django template variables like {{ client.name }}.",
    )

    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_templates",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_usage_display()})"


class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    SENDING = "sending", "Sending"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Campaign(models.Model):
    """
    Mass email campaign.

    Examples:
      - 'Diwali Wedding Offer 2025'
      - 'New Photography Package Launch'
    """
    name = models.CharField(max_length=150)
    template = models.ForeignKey(
        MessageTemplate,
        on_delete=models.PROTECT,
        limit_choices_to={"channel": Channel.EMAIL},
    )
    integration = models.ForeignKey(
        EmailIntegration,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="If blank, uses default integration",
    )

    subject_override = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional subject override; leave empty to use template subject.",
    )

    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT,
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Filters (optional): store your selection logic, e.g. a tag, segment name, etc.
    segment_description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable description of which clients/contacts are targeted.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="campaigns_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def subject(self):
        return self.subject_override or self.template.subject


class RecipientStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"

class CampaignRecipient(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    client = models.ForeignKey(
        Client,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaign_recipients",
    )
    contact = models.ForeignKey(
        Contact,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaign_recipients",
    )
    # NEW: event_person (for anniversary / event-based targeting)
    event_person = models.ForeignKey(
        EventPerson,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="campaign_recipients",
    )

    email = models.EmailField()

    status = models.CharField(
        max_length=20,
        choices=RecipientStatus.choices,
        default=RecipientStatus.PENDING,
    )
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    opened = models.BooleanField(default=False)
    clicked = models.BooleanField(default=False)

    class Meta:
        unique_together = ("campaign", "email")

    def __str__(self):
        return f"{self.email} ({self.campaign.name})"
