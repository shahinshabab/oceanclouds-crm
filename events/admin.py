# events/admin.py
from django.contrib import admin

from .models import (
    Venue,
    Event,
    ChecklistItem,
)


# -------- Inline Classes -------- #


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
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



# -------- EventPerson Admin -------- #


# -------- Checklist Admin -------- #


