# events/admin.py
from django.contrib import admin

from .models import (
    Venue,
    Event,
    EventTimelineItem,
    EventPerson,
    ChecklistItem,
    EventVendor,
)


# -------- Inline Classes -------- #

class EventTimelineItemInline(admin.TabularInline):
    model = EventTimelineItem
    extra = 1


class EventPersonInline(admin.TabularInline):
    model = EventPerson
    extra = 2  # Bride + Groom


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 1


class EventVendorInline(admin.TabularInline):
    model = EventVendor
    extra = 1


# -------- Venue Admin -------- #

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "venue_type",
        "city",
        "district",
        "state",
        "country",
        "capacity",
        "phone",
        "email",
    )
    list_filter = (
        "venue_type",
        "city",
        "district",
        "state",
        "country",
    )
    search_fields = (
        "name",
        "city",
        "district",
        "state",
        "country",
        "address_line1",
        "address_line2",
    )
    raw_id_fields = ("owner",)


# -------- Event Admin -------- #

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event_type",
        "status",
        "client",
        "primary_contact",
        "date",
        "start_time",
        "venue",
    )
    list_filter = ("event_type", "status", "date", "venue")
    search_fields = ("name", "client__name", "venue__name")
    raw_id_fields = ("client", "primary_contact", "venue", "owner")
    inlines = [
        EventTimelineItemInline,
        EventPersonInline,
        ChecklistItemInline,
        EventVendorInline,
    ]


# -------- EventPerson Admin -------- #

@admin.register(EventPerson)
class EventPersonAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "role",
        "event",
        "email",
        "phone",
        "allow_marketing",
    )
    list_filter = ("role", "allow_marketing", "event")
    search_fields = ("full_name", "email", "phone", "event__name")
    raw_id_fields = ("event", "owner")


# -------- Checklist Admin -------- #

@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event",
        "category",
        "is_done",
        "due_date",
        "assigned_to",
        "vendor",
    )
    list_filter = ("category", "is_done", "due_date", "event")
    search_fields = ("title", "event__name")
    raw_id_fields = ("event", "assigned_to", "vendor", "owner")


# -------- Event Vendor Admin -------- #

@admin.register(EventVendor)
class EventVendorAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "vendor",
        "service",
        "role",
        "cost_estimate",
        "cost_actual",
        "is_confirmed",
    )
    list_filter = ("is_confirmed", "vendor", "service", "event")
    search_fields = ("event__name", "vendor__name", "role")
    raw_id_fields = ("event", "vendor", "service", "owner")
