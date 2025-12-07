# messaging/admin.py
from django.contrib import admin
from .models import EmailIntegration, MessageTemplate, Campaign, CampaignRecipient

@admin.register(EmailIntegration)
class EmailIntegrationAdmin(admin.ModelAdmin):
    list_display = ("name", "backend_type", "channel", "is_default", "host", "from_email")
    list_editable = ("is_default",)
    search_fields = ("name", "host", "from_email")


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "channel", "usage", "is_active", "updated_at")
    list_filter = ("channel", "usage", "is_active")
    search_fields = ("name", "code", "subject")


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    readonly_fields = ("status", "sent_at", "last_error")


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "template", "status", "scheduled_for", "created_at")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [CampaignRecipientInline]
