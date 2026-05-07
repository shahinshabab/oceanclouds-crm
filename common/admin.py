from django.contrib import admin
from .models import Choice, Document, Communication


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

