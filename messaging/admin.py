# messaging/admin.py
from django.contrib import admin

from .models import EmailTemplate, Campaign, CampaignRecipient


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "type",
        "subject",
        "is_active",
        "is_default_for_type",
        "owner",
        "created_at",
    )
    list_filter = ("type", "is_active", "is_default_for_type", "created_at")
    search_fields = ("name", "subject", "body_html", "body_text")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at", "owner")

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "type", "is_active", "is_default_for_type"),
        }),
        ("Content", {
            "fields": ("subject", "body_html", "body_text"),
        }),
        ("Meta", {
            "fields": ("owner", "created_at", "updated_at"),
        }),
    )

    def save_model(self, request, obj, form, change):
        # Owned mixin => set owner once
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


class CampaignRecipientInline(admin.TabularInline):
    model = CampaignRecipient
    extra = 0
    fields = (
        "email",
        "first_name",
        "last_name",
        "company",
        "status",
        "sent_at",
        "last_error",
    )
    readonly_fields = ("status", "sent_at", "last_error", "created_at")
    can_delete = True


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "template",
        "status",
        "target_type",
        "start_date",
        "start_time",
        "weekdays_only",
        "daily_limit",
        "total_sent",
        "last_run_at",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "target_type",
        "weekdays_only",
        "start_date",
        "created_at",
    )
    search_fields = ("name", "description", "template__name")
    readonly_fields = ("last_run_at", "total_sent", "created_at", "updated_at", "owner")
    inlines = [CampaignRecipientInline]

    fieldsets = (
        (None, {
            "fields": ("name", "description", "template"),
        }),
        ("Sender", {
            "fields": ("from_email", "reply_to"),
        }),
        ("Targets", {
            "fields": ("target_type",),
        }),
        ("Scheduling & Throttling", {
            "fields": (
                "status",
                "start_date",
                "start_time",
                "weekdays_only",
                "daily_limit",
                "delay_seconds",
            ),
        }),
        ("Runtime", {
            "fields": ("total_sent", "last_run_at"),
        }),
        ("Meta", {
            "fields": ("owner", "created_at", "updated_at"),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.owner_id:
            obj.owner = request.user
        super().save_model(request, obj, form, change)


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "campaign",
        "status",
        "sent_at",
        "created_at",
    )
    list_filter = ("status", "campaign", "created_at")
    search_fields = ("email", "first_name", "last_name", "company", "campaign__name")
    readonly_fields = ("sent_at", "created_at", "updated_at", "last_error")
