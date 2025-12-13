# events/models.py
from django.conf import settings
from django.db import models
from django.db.models import Q, UniqueConstraint
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from common.models import TimeStamped, Owned
from crm.models import Client, Contact
from services.models import Vendor, Service
from django.utils import timezone

# -------------------------------------------------------------------
# Choice enums
# -------------------------------------------------------------------

class EventType(models.TextChoices):
    WEDDING = "wedding", _("Wedding")
    RECEPTION = "reception", _("Reception")
    MEHNDI = "mehndi", _("Mehndi")
    SANGEET = "sangeet", _("Sangeet")
    ENGAGEMENT = "engagement", _("Engagement")
    OTHER = "other", _("Other")


class EventStatus(models.TextChoices):
    TENTATIVE = "tentative", _("Tentative")
    PLANNED = "planned", _("Planned")
    CONFIRMED = "confirmed", _("Confirmed")
    COMPLETED = "completed", _("Completed")
    CANCELLED = "cancelled", _("Cancelled")


class VenueType(models.TextChoices):
    HOTEL = "hotel", _("Hotel")
    HALL = "hall", _("Function Hall")
    OUTDOOR = "outdoor", _("Outdoor")
    PRIVATE_PROPERTY = "private_property", _("Private Property")
    OTHER = "other", _("Other")


class RSVPStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACCEPTED = "accepted", _("Accepted")
    DECLINED = "declined", _("Declined")
    MAYBE = "maybe", _("Maybe")


class ChecklistCategory(models.TextChoices):
    LOGISTICS = "logistics", _("Logistics")
    DECOR = "decor", _("Decor")
    CATERING = "catering", _("Catering")
    PHOTOGRAPHY = "photography", _("Photography & Video")
    PROGRAM = "program", _("Program & Rituals")
    COMMUNICATION = "communication", _("Communication")
    PAYMENTS = "payments", _("Payments")
    OTHER = "other", _("Other")


class EventPersonRole(models.TextChoices):
    BRIDE = "bride", _("Bride")
    GROOM = "groom", _("Groom")
    OTHER = "other", _("Other / Family")


# -------------------------------------------------------------------
# Venue
# -------------------------------------------------------------------

class Venue(TimeStamped, Owned):
    """
    Event venue (hotel, hall, outdoor space).
    """

    name = models.CharField(max_length=255)
    venue_type = models.CharField(
        max_length=32,
        choices=VenueType.choices,
        default=VenueType.OTHER,
    )

    contact_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)

    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    district = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=128, blank=True, default="Kerala")
    country = models.CharField(max_length=128, blank=True, default="India")

    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Approximate maximum capacity."),
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self):
        return reverse("events:venue_detail", args=[self.pk])


# -------------------------------------------------------------------
# Event
# -------------------------------------------------------------------

class Event(TimeStamped, Owned):
    """
    Individual ceremony or function (wedding, reception, mehndi, etc.).
    """

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="events",
    )

    primary_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )

    name = models.CharField(
        max_length=255,
        help_text=_("Internal event name, e.g. 'Rohan & Aisha – Wedding Ceremony'."),
    )
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        default=EventType.WEDDING,
    )
    status = models.CharField(
        max_length=32,
        choices=EventStatus.choices,
        default=EventStatus.PLANNED,
    )

    date = models.DateField(
        help_text=_("Main event date (for multi-day events, use earliest)."),
    )
    start_time = models.TimeField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    venue = models.ForeignKey(
        Venue,
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )

    expected_guests = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Expected guest count."),
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("date", "start_time", "name")

    def __str__(self) -> str:
        return f"{self.name} ({self.date})"

    def get_absolute_url(self):
        return reverse("events:event_detail", args=[self.pk])


# -------------------------------------------------------------------
# Event Timeline
# -------------------------------------------------------------------

class EventTimelineItem(models.Model):
    """
    Schedule / run sheet entry for an event.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="timeline_items",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField(blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    assigned_vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        related_name="timeline_items",
        null=True,
        blank=True,
    )
    assigned_contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        related_name="timeline_items",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("event", "order", "start_time")

    def __str__(self) -> str:
        return f"{self.title} ({self.event})"


# -------------------------------------------------------------------
# Event People (Bride / Groom / Family)
# -------------------------------------------------------------------

class EventPerson(TimeStamped, Owned):
    """
    Key people for an event (bride, groom, parents, etc.).
    Used for anniversary wishes, offers, and feedback.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="people",
    )

    role = models.CharField(
        max_length=16,
        choices=EventPersonRole.choices,
        default=EventPersonRole.OTHER,
    )

    full_name = models.CharField(max_length=255)

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    whatsapp = models.CharField(
        max_length=32,
        blank=True,
        help_text=_("WhatsApp number if different from phone."),
    )

    # For marketing / offers
    allow_marketing = models.BooleanField(
        default=True,
        help_text=_("Allow anniversary wishes, offers, and follow-up messages."),
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("event", "role", "full_name")
        constraints = [
            UniqueConstraint(
                fields=["event", "role"],
                condition=Q(role__in=[EventPersonRole.BRIDE, EventPersonRole.GROOM]),
                name="unique_bride_groom_per_event",
            )
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_role_display()} – {self.event})"


# -------------------------------------------------------------------
# Checklist
# -------------------------------------------------------------------

class ChecklistItem(TimeStamped, Owned):
    """
    Planning checklist item per event.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="checklist_items",
    )
    title = models.CharField(max_length=255)
    category = models.CharField(
        max_length=32,
        choices=ChecklistCategory.choices,
        default=ChecklistCategory.OTHER,
    )

    is_done = models.BooleanField(default=False)
    due_date = models.DateField(null=True, blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="event_tasks",
        null=True,
        blank=True,
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.SET_NULL,
        related_name="checklist_items",
        null=True,
        blank=True,
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("event", "due_date", "title")

    def __str__(self) -> str:
        return f"{self.title} ({self.event})"


# -------------------------------------------------------------------
# Event Vendors
# -------------------------------------------------------------------

class EventVendor(TimeStamped, Owned):
    """
    Vendor assignment for an event with cost tracking.
    """

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="event_vendors",
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name="event_assignments",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="event_assignments",
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=255,
        help_text=_("Role for this event, e.g. 'Main Decor', 'Photo & Video'."),
    )

    cost_estimate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Estimated vendor cost."),
    )
    cost_actual = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Actual final vendor cost."),
    )
    is_confirmed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("event", "vendor__name")
        unique_together = ("event", "vendor", "service")

    def __str__(self) -> str:
        return f"{self.vendor} for {self.event}"


class AnniversaryWishLog(TimeStamped):
    """
    One row per person per year to avoid sending duplicate wishes.
    """
    person = models.ForeignKey(
        EventPerson,
        on_delete=models.CASCADE,
        related_name="anniversary_wish_logs",
    )
    year = models.PositiveIntegerField()
    sent_at = models.DateTimeField(default=timezone.now)
    message_id = models.CharField(max_length=255, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["person", "year"], name="uniq_anniversary_wish_per_person_year")
        ]
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.person.full_name} - {self.year}"
