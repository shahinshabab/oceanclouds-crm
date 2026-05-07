# events/admin.py

from django.contrib import admin

from .models import Venue, Event, EventChecklist, ChecklistItem


class EventChecklistInline(admin.StackedInline):
    model = EventChecklist
    extra = 0
    max_num = 1
    fields = (
        "owner",
        "title",
        "notes",
        "created_at",
        "updated_at",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)


class ChecklistItemInline(admin.TabularInline):
    model = ChecklistItem
    extra = 0
    fields = (
        "title",
        "category",
        "is_done",
        "due_date",
        "assigned_to",
        "owner",
    )
    autocomplete_fields = (
        "assigned_to",
        "owner",
    )


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "venue_type",
        "contact_name",
        "phone",
        "email",
        "city",
        "district",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "venue_type",
        "is_active",
        "state",
        "country",
        "created_at",
    )
    search_fields = (
        "name",
        "contact_name",
        "phone",
        "email",
        "city",
        "district",
        "notes",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)
    fieldsets = (
        ("Venue Details", {
            "fields": (
                "owner",
                "name",
                "venue_type",
                "is_active",
            )
        }),
        ("Contact", {
            "fields": (
                "contact_name",
                "phone",
                "email",
            )
        }),
        ("Address", {
            "fields": (
                "address_line1",
                "address_line2",
                "city",
                "district",
                "state",
                "country",
            )
        }),
        ("Notes", {
            "fields": ("notes",)
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "event_type",
        "status",
        "date",
        "start_time",
        "end_time",
        "client",
        "primary_contact",
        "venue",
        "project",
        "owner",
        "created_at",
    )
    list_filter = (
        "event_type",
        "status",
        "date",
        "vendor_template_sent",
        "client_template_sent",
        "created_at",
    )
    search_fields = (
        "name",
        "notes",
        "internal_notes",
        "client__name",
        "client__display_name",
        "primary_contact__first_name",
        "primary_contact__last_name",
        "venue__name",
        "project__name",
    )
    readonly_fields = (
        "vendor_template_sent_at",
        "client_template_sent_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "project",
        "client",
        "primary_contact",
        "venue",
        "services",
        "packages",
        "vendors",
        "inventory_items",
    )
    filter_horizontal = (
        "services",
        "packages",
        "vendors",
        "inventory_items",
    )
    inlines = (EventChecklistInline,)
    fieldsets = (
        ("Event Details", {
            "fields": (
                "owner",
                "name",
                "event_type",
                "status",
                "date",
                "start_time",
                "end_time",
            )
        }),
        ("Linked Records", {
            "fields": (
                "project",
                "client",
                "primary_contact",
                "venue",
            )
        }),
        ("Services / Resources", {
            "fields": (
                "services",
                "packages",
                "vendors",
                "inventory_items",
            )
        }),
        ("Notes", {
            "fields": (
                "notes",
                "internal_notes",
            )
        }),
        ("Messaging Status", {
            "fields": (
                "vendor_template_sent",
                "client_template_sent",
                "vendor_template_sent_at",
                "client_template_sent_at",
            ),
            "classes": ("collapse",),
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(EventChecklist)
class EventChecklistAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event",
        "total_items",
        "done_items",
        "pending_items",
        "owner",
        "created_at",
    )
    list_filter = (
        "event__date",
        "created_at",
    )
    search_fields = (
        "title",
        "notes",
        "event__name",
        "event__client__name",
        "event__client__display_name",
    )
    readonly_fields = (
        "total_items",
        "done_items",
        "pending_items",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "event",
    )
    inlines = (ChecklistItemInline,)


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "checklist",
        "event",
        "category",
        "is_done",
        "due_date",
        "assigned_to",
        "owner",
        "created_at",
    )
    list_filter = (
        "category",
        "is_done",
        "due_date",
        "assigned_to",
        "created_at",
    )
    search_fields = (
        "title",
        "notes",
        "checklist__title",
        "checklist__event__name",
        "assigned_to__username",
        "assigned_to__first_name",
        "assigned_to__last_name",
    )
    readonly_fields = (
        "event",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "checklist",
        "assigned_to",
    )