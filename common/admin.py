from django.contrib import admin
from django.utils import timezone
from .models import Choice, Document, Communication, Ticket


@admin.register(Choice)
class ChoiceAdmin(admin.ModelAdmin):
    list_display = ("type", "value", "is_active", "created_at")
    search_fields = ("type", "value")
    list_filter = ("type", "is_active")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "file", "created_at")
    list_display = ("title", "file", "related_client", "related_deal", "related_event", "created_at")
    search_fields = ("title", "description")
    list_filter = ("created_at",)


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = (
        "channel",
        "subject",
        "client",
        "contact",
        "lead",
        "sent_by",
        "timestamp",
    )
    search_fields = ("subject", "message")
    list_filter = ("channel", "sent_by", "timestamp")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "created_by", "priority", "status", "created_at")
    list_filter = ("status", "priority")
    search_fields = ("subject", "description", "created_by__email")
    readonly_fields = ("created_at", "updated_at", "responded_at")

    fieldsets = (
        ("Ticket Info", {
            "fields": ("subject", "description", "priority", "status")
        }),
        ("Users", {
            "fields": ("created_by", "assigned_to")
        }),
        ("Support Response", {
            "fields": ("admin_response", "responded_at")
        }),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        if "admin_response" in form.changed_data:
            obj.responded_at = timezone.now()
        super().save_model(request, obj, form, change)
