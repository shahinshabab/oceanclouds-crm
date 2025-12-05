# crm/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint

from common.models import TimeStamped, Owned  # assuming these exist in `common`


class Client(TimeStamped, Owned):
    """
    Main paying customer (family or individual).
    Replaces 'Company' from generic CRM.
    """

    name = models.CharField(
        max_length=255,
        help_text="Family name or primary client name",
    )
    display_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional shorter name used in UI (e.g. 'Anita & Rohan Wedding').",
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    instagram_handle = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)

    billing_address = models.TextField(blank=True)

    city = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True, default="Kerala")
    country = models.CharField(max_length=100, blank=True, default="India")

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self) -> str:
        return self.display_name or self.name

    @property
    def primary_contact(self):
        """
        Convenience property to get the primary contact for this client.
        """
        return self.contacts.filter(is_primary=True).first()


class Contact(TimeStamped, Owned):
    """
    Individual person linked to a Client (bride, groom, parent, assistant, etc.).
    """

    ROLE_CHOICES = [
        ("bride", "Bride"),
        ("groom", "Groom"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("friend", "Friend"),
        ("planner", "External Wedding Planner"),
        ("other", "Other"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="contacts",
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        blank=True,
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)

    is_primary = models.BooleanField(
        default=False,
        help_text="Main decision maker / primary point of contact for this client.",
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["client__name", "first_name"]
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        # Only enforce uniqueness when email is non-empty
        constraints = [
            UniqueConstraint(
                fields=["client", "email"],
                condition=~Q(email=""),
                name="uniq_contact_email_per_client_non_empty",
            )
        ]

    def __str__(self) -> str:
        full_name = f"{self.first_name} {self.last_name}".strip()
        return f"{full_name} ({self.client})"


class Lead(TimeStamped, Owned):
    """
    Unqualified inquiry that may convert into a Client + Deal.
    """

    STATUS_CHOICES = [
        ("new", "New"),
        ("contacted", "Contacted"),
        ("qualified", "Qualified"),
        ("proposal_sent", "Proposal Sent"),
        ("lost", "Lost"),
        ("converted", "Converted to Client"),
    ]

    SOURCE_CHOICES = [
        ("website", "Website"),
        ("instagram", "Instagram"),
        ("whatsapp", "WhatsApp"),
        ("referral", "Referral"),
        ("friend", "Friend"),
        ("exhibition", "Exhibition / Expo"),
        ("other", "Other"),
    ]

    # Single display name for the lead (you simplified this, good)
    name = models.CharField(max_length=100)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp = models.CharField(max_length=50, blank=True)

    # Optional – expected wedding date & location
    wedding_date = models.DateField(null=True, blank=True)
    wedding_city = models.CharField(max_length=100, blank=True)
    wedding_district = models.CharField(max_length=100, blank=True)
    wedding_state = models.CharField(max_length=100, blank=True, default="Kerala")
    wedding_country = models.CharField(max_length=100, blank=True, default="India")

    # Budget range (approx)
    budget_min = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    budget_max = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="new",
    )

    # ---- Source info ----
    source = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        blank=True,
        help_text="Where this lead came from (Website, Instagram, WhatsApp, Referral, Friend, etc.).",
    )
    source_detail = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional extra detail (e.g. referrer name, specific campaign, event name).",
    )

    notes = models.TextField(blank=True)

    next_action_date = models.DateField(null=True, blank=True)
    next_action_note = models.CharField(max_length=255, blank=True)

    # If converted:
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


class Inquiry(TimeStamped, Owned):
    """
    Raw incoming inquiry (website form, call log, WhatsApp, etc.).
    Can be linked to a Lead and/or Client.
    """

    CHANNEL_CHOICES = [
        ("website", "Website Form"),
        ("phone", "Phone Call"),
        ("whatsapp", "WhatsApp"),
        ("instagram", "Instagram DM"),
        ("facebook", "Facebook"),
        ("email", "Email"),
        ("referral", "Referral"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("open", "Open"),
        ("in_progress", "In Progress"),
        ("closed", "Closed"),
        ("converted", "Converted to Lead"),
    ]

    channel = models.CharField(
        max_length=50,
        choices=CHANNEL_CHOICES,
        default="instagram",
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default="open",
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of inquirer",
    )
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    wedding_date = models.DateField(null=True, blank=True)
    wedding_city = models.CharField(max_length=100, blank=True)
    wedding_district = models.CharField(max_length=100, blank=True)
    wedding_state = models.CharField(max_length=100, blank=True, default="Kerala")
    wedding_country = models.CharField(max_length=100, blank=True, default="India")

    message = models.TextField(blank=True)

    # Relations
    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inquiries",
    )

    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="handled_inquiries",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    def __str__(self) -> str:
        return f"{self.get_channel_display()} - {self.name or self.email or self.phone}"
    
class ClientReview(TimeStamped, Owned):
    """
    Feedback / review given by a client.
    Typically collected after an event or project completion.
    """

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="reviews",
        help_text="Client who gave this review.",
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Overall rating from 1–5 (optional).",
    )

    title = models.CharField(
        max_length=255,
        blank=True,
        help_text="Short summary of the review (optional).",
    )

    comment = models.TextField(
        blank=True,
        help_text="Full review text / feedback from the client.",
    )

    # NEW — next action to be taken
    next_action = models.CharField(
        max_length=255,
        blank=True,
        help_text="Next follow-up action for this review (optional).",
    )

    # NEW — next action date
    next_action_date = models.DateField(
        null=True,
        blank=True,
        help_text="Due date for next action (optional).",
    )

    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="client_reviews_responded",
        help_text="Team member who responded to this review (if any).",
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When we responded to this review (optional).",
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Client Review"
        verbose_name_plural = "Client Reviews"

    def __str__(self):
        base = self.title or (self.comment[:30] + "..." if self.comment else "Review")
        return f"{base} – {self.client}"

    @property
    def has_rating(self) -> bool:
        return self.rating is not None

