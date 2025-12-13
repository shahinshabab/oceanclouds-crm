# messaging/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStamped, Owned  # 🔹 use your shared mixins

class EmailTemplate(TimeStamped, Owned):
    """
    Store reusable email templates for different purposes:
    - campaign
    - proposal
    - contract
    - invoice
    - payment
    - anniversary
    """

    class TemplateType(models.TextChoices):
        CAMPAIGN = "campaign", "Campaign"
        PROPOSAL = "proposal", "Proposal"
        CONTRACT = "contract", "Contract"
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        ANNIVERSARY = "anniversary", "Anniversary"

    name = models.CharField(max_length=200)
    slug = models.SlugField(
        unique=True,
        help_text=(
            "Unique identifier used by the system and automation. "
            "Use lowercase letters, numbers and hyphens only "
            "(e.g. 'campaign-welcome')."
        ),
    )


    type = models.CharField(
        max_length=20,
        choices=TemplateType.choices,
        default=TemplateType.CAMPAIGN,
        help_text="Where this template is used.",
    )
    subject = models.CharField(max_length=255)
    body_html = models.TextField(
        help_text=(
            "HTML body. You can use Django template variables like "
            "{{ client.name }}, {{ deal.title }}, {{ event.date }}."
        )
    )
    body_text = models.TextField(
        blank=True,
        help_text="Optional plain-text version (for clients that do not support HTML).",
    )

    is_active = models.BooleanField(default=True)
    is_default_for_type = models.BooleanField(
        default=False,
        help_text=(
            "If true, this will be used as the default template for this type "
            "(e.g. default proposal template)."
        ),
    )

    class Meta:
        ordering = ["type", "name"]
        verbose_name = "Email template"
        verbose_name_plural = "Email templates"

    def __str__(self):
        return f"{self.get_type_display()} - {self.name}"


class Campaign(TimeStamped, Owned):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    class TargetType(models.TextChoices):
        CUSTOM_LIST = "custom_list", "Custom list (paste recipients)"
        CLIENT_MARKETING = "client_marketing", "Clients (contacts with allow marketing)"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.PROTECT,
        related_name="campaigns",
        limit_choices_to={"type": EmailTemplate.TemplateType.CAMPAIGN},
    )

    from_email = models.EmailField(
        default="noreply@oceanclouds.in",
        help_text="Sender email. Defaults to AWS_SES_SENDER if left blank.",
        blank=True,
    )
    reply_to = models.EmailField(
        default="help@oceanclouds.in",
        help_text="Reply-to email. Defaults to AWS_SES_SENDER if left blank.",
        blank=True,
    )

    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
        default=TargetType.CUSTOM_LIST,
        help_text="How recipients are selected for this campaign.",
    )

    # NEW: store pasted list
    custom_list_raw = models.TextField(
        blank=True,
        help_text=(
            "Used only when Target Type is Custom list. "
            "Enter one recipient per line as: Name, email@example.com (or just email@example.com)."
        ),
    )

    # scheduling / throttling
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    start_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    weekdays_only = models.BooleanField(default=True)
    daily_limit = models.PositiveIntegerField(default=20)
    delay_seconds = models.PositiveIntegerField(default=5)

    last_run_at = models.DateTimeField(null=True, blank=True)
    total_sent = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def effective_from_email(self):
        return self.from_email or getattr(settings, "AWS_SES_SENDER", "")


class CampaignRecipient(TimeStamped):
    """
    Concrete recipients for a campaign.

    For TargetType.CUSTOM_LIST, these are the main source.
    For other target types, you can pre-populate from crm.Client / crm.Contact etc.
    """

    class SendStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    email = models.EmailField()
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    company = models.CharField(max_length=255, blank=True)

    status = models.CharField(
        max_length=20,
        choices=SendStatus.choices,
        default=SendStatus.PENDING,
    )
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("campaign", "email")
        ordering = ["campaign", "email"]

    def __str__(self):
        return f"{self.email} ({self.campaign.name})"

    def mark_sent(self):
        self.status = self.SendStatus.SENT
        self.sent_at = timezone.now()
        self.last_error = ""
        self.save(update_fields=["status", "sent_at", "last_error"])
