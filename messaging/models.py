# messaging/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from common.models import TimeStamped, Owned


class EmailTemplate(TimeStamped, Owned):
    class TemplateType(models.TextChoices):
        CAMPAIGN = "campaign", "Campaign"
        PROPOSAL = "proposal", "Proposal"
        CONTRACT = "contract", "Contract"
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        ANNIVERSARY = "anniversary", "Anniversary"

    class PdfAttachmentMode(models.TextChoices):
        NONE = "none", "No generated PDF"
        RELATED_OBJECT = "related_object", "Attach generated PDF from related record"

    name = models.CharField(max_length=200)

    slug = models.SlugField(
        unique=True,
        help_text="Example: proposal-default, invoice-default, anniversary-wish",
    )

    type = models.CharField(
        max_length=30,
        choices=TemplateType.choices,
        default=TemplateType.CAMPAIGN,
    )

    subject = models.CharField(
        max_length=255,
        help_text="Example: Proposal from {{ company_name }} - {{ proposal.title }}",
    )

    body_html = models.TextField(
        help_text=(
            "HTML email body. You can use variables like "
            "{{ client.name }}, {{ proposal.title }}, {{ invoice.total_amount }}."
        )
    )

    body_text = models.TextField(
        blank=True,
        help_text="Optional plain text fallback.",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Only one active template is allowed for each type.",
    )

    is_default_for_type = models.BooleanField(
        default=True,
        help_text="Active template will be treated as the default for this type.",
    )

    attach_generated_pdf = models.BooleanField(
        default=False,
        help_text="If enabled, the related generated PDF will be attached when available.",
    )

    pdf_attachment_mode = models.CharField(
        max_length=30,
        choices=PdfAttachmentMode.choices,
        default=PdfAttachmentMode.NONE,
    )

    class Meta:
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["type"],
                condition=Q(is_active=True),
                name="only_one_active_email_template_per_type",
            )
        ]

    def clean(self):
        super().clean()

        if self.attach_generated_pdf and self.pdf_attachment_mode == self.PdfAttachmentMode.NONE:
            raise ValidationError({
                "pdf_attachment_mode": "Select related object PDF mode when generated PDF attachment is enabled."
            })

        if self.is_active:
            self.is_default_for_type = True

    def save(self, *args, **kwargs):
        if self.is_active:
            self.is_default_for_type = True
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.get_type_display()} - {self.name} ({status})"


class EmailTemplateAttachment(TimeStamped):
    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="email_template_attachments/%Y/%m/",
        help_text="Optional image, PDF, or file attached with this template.",
    )

    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional file name shown in the email attachment.",
    )

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.display_name or self.file.name


class EmailSendLog(TimeStamped):
    class Status(models.TextChoices):
        SKIPPED = "skipped", "Skipped"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="send_logs",
    )

    template_type = models.CharField(max_length=30, blank=True)

    to_email = models.EmailField()
    subject = models.CharField(max_length=255, blank=True)

    related_model = models.CharField(max_length=100, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SKIPPED,
    )

    ses_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_sent(self, message_id=""):
        self.status = self.Status.SENT
        self.ses_message_id = message_id or ""
        self.sent_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "ses_message_id", "sent_at", "error_message"])

    def mark_failed(self, error):
        self.status = self.Status.FAILED
        self.error_message = str(error)
        self.save(update_fields=["status", "error_message"])


class Campaign(TimeStamped, Owned):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        COMPLETED = "completed", "Completed"

    class TargetType(models.TextChoices):
        CLIENT_MARKETING = "client_marketing", "Client contacts with allow marketing"
        ANNIVERSARY = "anniversary", "Bride/Groom anniversary contacts"

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.PROTECT,
        related_name="campaigns",
        limit_choices_to={"type": EmailTemplate.TemplateType.CAMPAIGN, "is_active": True},
    )

    target_type = models.CharField(
        max_length=30,
        choices=TargetType.choices,
        default=TargetType.CLIENT_MARKETING,
    )

    from_email = models.EmailField(blank=True)
    reply_to = models.EmailField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    start_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)

    weekdays_only = models.BooleanField(default=True)
    daily_limit = models.PositiveIntegerField(default=50)
    delay_seconds = models.PositiveIntegerField(default=5)

    last_run_at = models.DateTimeField(null=True, blank=True)
    total_sent = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def effective_from_email(self):
        return self.from_email or getattr(settings, "EMAIL_DEFAULT_FROM", "") or getattr(settings, "AWS_SES_SENDER", "")

    @property
    def effective_reply_to(self):
        return self.reply_to or getattr(settings, "EMAIL_DEFAULT_REPLY_TO", "") or getattr(settings, "AWS_SES_SENDER", "")


class CampaignRecipient(TimeStamped):
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

    client_id = models.PositiveIntegerField(null=True, blank=True)
    contact_id = models.PositiveIntegerField(null=True, blank=True)

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

    def mark_failed(self, error):
        self.status = self.SendStatus.FAILED
        self.last_error = str(error)
        self.save(update_fields=["status", "last_error"])


class WhatsAppTemplate(TimeStamped, Owned):
    class TemplateType(models.TextChoices):
        EVENT_CLIENT = "event_client", "Event - Client"
        EVENT_VENDOR = "event_vendor", "Event - Vendor"
        PROPOSAL = "proposal", "Proposal"
        CONTRACT = "contract", "Contract"
        INVOICE = "invoice", "Invoice"
        PAYMENT = "payment", "Payment"
        ANNIVERSARY = "anniversary", "Anniversary"
        CUSTOM = "custom", "Custom"

    class Provider(models.TextChoices):
        META = "meta", "Meta WhatsApp Cloud API"
        MSG91 = "msg91", "MSG91"

    class Category(models.TextChoices):
        UTILITY = "UTILITY", "Utility"
        MARKETING = "MARKETING", "Marketing"
        AUTHENTICATION = "AUTHENTICATION", "Authentication"

    class Language(models.TextChoices):
        EN = "en", "English"
        EN_US = "en_US", "English US"
        EN_GB = "en_GB", "English UK"
        ML = "ml", "Malayalam"
        HI = "hi", "Hindi"

    name = models.CharField(max_length=200)

    slug = models.SlugField(
        unique=True,
        help_text="Example: event-client-default, event-vendor-default",
    )

    type = models.CharField(
        max_length=40,
        choices=TemplateType.choices,
        default=TemplateType.EVENT_CLIENT,
    )

    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.META,
    )

    provider_template_name = models.CharField(
        max_length=255,
        help_text="Exact approved template name in Meta/MSG91. Example: event_client_update",
    )

    language_code = models.CharField(
        max_length=20,
        choices=Language.choices,
        default=Language.EN,
        help_text="Must match approved WhatsApp template language.",
    )

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.UTILITY,
    )

    body_text = models.TextField(
        help_text=(
            "Internal preview body. Use Django variables like "
            "{{ event.name }}, {{ client.name }}, {{ venue.name }}. "
            "This is for your preview/log only. Actual WhatsApp template text is approved in provider."
        )
    )

    header_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional internal preview header.",
    )

    footer_text = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional internal preview footer.",
    )

    # Store variables in order because WhatsApp templates use positional params.
    # Example:
    # ["event.name", "event.date", "venue.name"]
    variable_order = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Ordered variables for WhatsApp template parameters. "
            "Example: [\"event.name\", \"event.date\", \"venue.name\"]"
        ),
    )

    is_active = models.BooleanField(default=True)

    is_default_for_type = models.BooleanField(
        default=True,
        help_text="Only one active default WhatsApp template per type/provider/language.",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["type", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["type", "provider", "language_code"],
                condition=Q(is_active=True, is_default_for_type=True),
                name="only_one_active_whatsapp_template_per_type_provider_lang",
            )
        ]

    def clean(self):
        super().clean()

        if self.is_active:
            self.is_default_for_type = True

        if not self.provider_template_name:
            raise ValidationError({
                "provider_template_name": "Provider template name is required."
            })

    def save(self, *args, **kwargs):
        if self.is_active:
            self.is_default_for_type = True
        super().save(*args, **kwargs)

    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"{self.get_type_display()} - {self.name} ({status})"


class WhatsAppSendLog(TimeStamped):
    class Status(models.TextChoices):
        SKIPPED = "skipped", "Skipped"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class Provider(models.TextChoices):
        META = "meta", "Meta WhatsApp Cloud API"
        MSG91 = "msg91", "MSG91"

    template = models.ForeignKey(
        WhatsAppTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="send_logs",
    )

    template_type = models.CharField(max_length=40, blank=True)
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.META,
    )

    to_number = models.CharField(max_length=32)
    rendered_message = models.TextField(blank=True)

    related_model = models.CharField(max_length=100, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SKIPPED,
    )

    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_sent(self, message_id="", raw_response=None):
        self.status = self.Status.SENT
        self.provider_message_id = message_id or ""
        self.sent_at = timezone.now()
        self.error_message = ""
        self.raw_response = raw_response or {}
        self.save(update_fields=[
            "status",
            "provider_message_id",
            "sent_at",
            "error_message",
            "raw_response",
        ])

    def mark_failed(self, error, raw_response=None):
        self.status = self.Status.FAILED
        self.error_message = str(error)
        self.raw_response = raw_response or {}
        self.save(update_fields=["status", "error_message", "raw_response"])