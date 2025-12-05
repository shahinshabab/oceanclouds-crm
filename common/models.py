# common/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
import os

# ----------------------------------------------------------------------
# ABSTRACT MODELS
# ----------------------------------------------------------------------


class TimeStamped(models.Model):
    """
    Adds created_at / updated_at timestamps to each model.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDelete(models.Model):
    """
    Adds soft delete: instead of deleting objects,
    mark them as inactive via is_deleted.
    """

    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """
        Soft-delete: mark as deleted instead of removing the row.
        """
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])


class Owned(models.Model):
    """
    Tracks which user created/owns the object.
    Useful for multi-user CRM (Admin, Manager, Employee).
    """

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_owned",
        help_text="User who created or owns this record.",
    )

    class Meta:
        abstract = True


# ----------------------------------------------------------------------
# GENERIC CHOICE TABLE
# ----------------------------------------------------------------------


class Choice(TimeStamped):
    """
    Generic choice table for dropdowns:
    - Lead source
    - Vendor type
    - Service category
    - Task priority
    - etc.

    Example:
        Choice(type="lead_source", value="Instagram")
    """

    type = models.CharField(
        max_length=50,
        help_text="Machine key for the group of choices, e.g. 'lead_source', 'vendor_type'.",
        db_index=True,
    )
    value = models.CharField(
        max_length=255,
        help_text="Human-readable value shown in dropdown, e.g. 'Instagram'.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ["type", "value"]
        ordering = ["type", "value"]
        verbose_name = "Choice"
        verbose_name_plural = "Choices"

    def __str__(self):
        return f"{self.type}: {self.value}"


# ----------------------------------------------------------------------
# DOCUMENT STORAGE
# ----------------------------------------------------------------------


class Document(TimeStamped, Owned):
    """
    Universal document model used across CRM:
    - Proposal PDFs
    - Invoices
    - Contracts
    - Event checklists
    - Client-uploaded files
    """

    file = models.FileField(
        upload_to="documents/%Y/%m/%d/",
        help_text="Uploaded file (PDF, image, etc.).",
    )
    title = models.CharField(
        max_length=255,
        help_text="Short title for this document.",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description or notes about this document.",
    )

    related_client = models.ForeignKey(
        "crm.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Client this document is primarily related to.",
    )

    related_deal = models.ForeignKey(
        "sales.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Deal/booking this document is related to.",
    )

    related_event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        help_text="Event this document is related to.",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    def __str__(self):
        return self.title


# ----------------------------------------------------------------------
# COMMUNICATION LOGS
# ----------------------------------------------------------------------


class Communication(TimeStamped, Owned):
    """
    Logs communication:
    - Email
    - SMS
    - WhatsApp
    - Call summary
    """

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
        ("call", "Phone Call"),
    ]

    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        help_text="Medium used for this communication.",
    )
    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Subject or short summary of the communication.",
    )
    message = models.TextField(
        blank=True,
        help_text="Full message body or call summary.",
    )

    client = models.ForeignKey(
        "crm.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communications",
        help_text="Client this communication is associated with.",
    )

    contact = models.ForeignKey(
        "crm.Contact",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communications",
        help_text="Specific contact person (bride, groom, etc.) involved.",
    )

    lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="communications",
        help_text="Lead this communication is tied to, if any.",
    )

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_communications",
        help_text="User who sent or logged this communication.",
    )

    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When this communication was sent or took place.",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Communication"
        verbose_name_plural = "Communications"

    def __str__(self):
        return f"{self.get_channel_display()} - {self.subject or 'No subject'}"


# ----------------------------------------------------------------------
# SYSTEM SETTINGS
# ----------------------------------------------------------------------


class SystemSetting(TimeStamped):
    """
    Global system configuration (single-row table in practice).
    """

    site_name = models.CharField(
        max_length=200,
        default="Wedding CRM",
        help_text="Name shown in the header/title of the site.",
    )
    company_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Your business/legal entity name.",
    )
    default_currency = models.CharField(
        max_length=10,
        default="AED",
        help_text="Default currency code (e.g. AED, INR, USD).",
    )
    timezone = models.CharField(
        max_length=50,
        default="Asia/Dubai",
        help_text="Default timezone string for the app.",
    )
    support_email = models.EmailField(
        blank=True,
        help_text="Support or contact email shown to users.",
    )
    allow_self_registration = models.BooleanField(
        default=False,
        help_text="Allow new users to sign up themselves.",
    )

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"


# ----------------------------------------------------------------------
# NOTIFICATIONS
# ----------------------------------------------------------------------


class Notification(models.Model):
    """
    Simple in-app notification model.
    Can point to Project, Task, Deliverable, etc. via GenericForeignKey.
    """

    class Type(models.TextChoices):
        PROJECT_ASSIGNED = "project_assigned", "Project assigned"
        TASK_ASSIGNED = "task_assigned", "Task assigned"
        OVERDUE = "overdue", "Overdue"
        DELIVERABLE_OVERDUE = "deliverable_overdue", "Deliverable overdue"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User who will see this notification.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications_sent",
        help_text="User who triggered this notification, if any.",
    )
    notif_type = models.CharField(
        max_length=32,
        choices=Type.choices,
        help_text="Type/category of this notification.",
    )

    # Generic relation to any target object (Project, Task, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey("content_type", "object_id")

    message = models.CharField(
        max_length=255,
        blank=True,
        help_text="Human-readable notification text.",
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Marked as read once user sees/acknowledges it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self):
        return self.message or f"{self.get_notif_type_display()}"

    def get_target_url(self):
        """
        Optional helper: assumes your target models implement get_absolute_url().
        """
        if self.target and hasattr(self.target, "get_absolute_url"):
            return self.target.get_absolute_url()
        return "#"

# ----------------------------------------------------------------------
# SUPPORT TICKET SYSTEM
# ----------------------------------------------------------------------
class TicketStatus(models.TextChoices):
    OPEN = "open", "Open"
    IN_PROGRESS = "in_progress", "In Progress"
    RESOLVED = "resolved", "Resolved"
    CLOSED = "closed", "Closed"


class TicketPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class TicketCategory(models.TextChoices):
    GENERAL = "general", "General"
    CRM = "crm", "CRM / Clients"
    SALES = "sales", "Sales / Deals"
    EVENTS = "events", "Events / Venues"
    PROJECTS = "projects", "Projects / Tasks"
    UI = "ui", "UI / Design"
    BILLING = "billing", "Billing / Payments"


class TicketSubject(models.TextChoices):
    BUG = "bug", "Bug / Error"
    FEATURE = "feature", "Feature Request"
    HOWTO = "howto", "How-to Question"
    DATA = "data_issue", "Data Issue"
    PERFORMANCE = "performance", "Slow / Performance"
    OTHER = "other", "Other"


def ticket_screenshot_upload_to(instance, filename):
    """
    Save screenshot as: ticketNumber_timestamp.ext
    Example: ticket_15_20251205T210301.png
    """
    base, ext = os.path.splitext(filename)
    timestamp = timezone.now().strftime("%Y%m%dT%H%M%S")
    ticket_no = instance.ticket_number or "tmp"
    return f"ticket_screenshots/ticket_{ticket_no}_{timestamp}{ext}"
    

class Ticket(TimeStamped):
    """
    Support ticket raised by any authenticated user.
    Only the designated support/admin user will respond through admin.
    """

    # Auto-incrementing ticket number (separate from pk)
    ticket_number = models.PositiveIntegerField(
        unique=True,
        editable=False,
        null=True,
        blank=True,
        help_text="Human-friendly ticket number.",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="support_tickets",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_support_tickets",
        null=True,
        blank=True,
    )

    category = models.CharField(
        max_length=20,
        choices=TicketCategory.choices,
        default=TicketCategory.GENERAL,
    )

    subject_type = models.CharField(
        max_length=20,
        choices=TicketSubject.choices,
        default=TicketSubject.OTHER,
    )

    subject = models.CharField(max_length=200)
    # Detailed description
    description = models.TextField()

    priority = models.CharField(
        max_length=20,
        choices=TicketPriority.choices,
        default=TicketPriority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=TicketStatus.choices,
        default=TicketStatus.OPEN,
    )

    # Optional screenshot, saved with ticket_number + timestamp
    screenshot = models.ImageField(
        upload_to=ticket_screenshot_upload_to,
        null=True,
        blank=True,
        help_text="Optional screenshot (PNG/JPG).",
    )

    admin_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Ticket #{self.ticket_number or self.pk} - {self.subject}"

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        # Assign auto-increment ticket_number if not set
        if self.ticket_number is None:
            last = Ticket.objects.order_by("-ticket_number").first()
            self.ticket_number = (last.ticket_number + 1) if last and last.ticket_number else 1
        super().save(*args, **kwargs)
