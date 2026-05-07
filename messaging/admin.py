# messaging/admin.py

from django.contrib import admin

from .models import (
    EmailTemplate,
    EmailTemplateAttachment,
    EmailSendLog,
    Campaign,
    CampaignRecipient,
    WhatsAppTemplate,
    WhatsAppSendLog,
)


class EmailTemplateAttachmentInline(admin.TabularInline):
    model = EmailTemplateAttachment
    extra = 0
    fields = (
        "file",
        "display_name",
        "is_active",
        "created_at",
    )
    readonly_fields = ("created_at",)


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
    readonly_fields = (
        "sent_at",
        "last_error",
    )


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "type",
        "is_active",
        "is_default_for_type",
        "attach_generated_pdf",
        "pdf_attachment_mode",
        "owner",
        "created_at",
    )
    list_filter = (
        "type",
        "is_active",
        "is_default_for_type",
        "attach_generated_pdf",
        "pdf_attachment_mode",
        "created_at",
    )
    search_fields = (
        "name",
        "slug",
        "subject",
        "body_html",
        "body_text",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)
    prepopulated_fields = {
        "slug": ("name",),
    }
    inlines = (EmailTemplateAttachmentInline,)
    fieldsets = (
        ("Template Details", {
            "fields": (
                "owner",
                "name",
                "slug",
                "type",
                "subject",
                "is_active",
                "is_default_for_type",
            )
        }),
        ("Body", {
            "fields": (
                "body_html",
                "body_text",
            )
        }),
        ("PDF Attachment", {
            "fields": (
                "attach_generated_pdf",
                "pdf_attachment_mode",
            )
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(EmailTemplateAttachment)
class EmailTemplateAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "template",
        "display_name",
        "file",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "created_at",
    )
    search_fields = (
        "template__name",
        "template__slug",
        "display_name",
        "file",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("template",)


@admin.register(EmailSendLog)
class EmailSendLogAdmin(admin.ModelAdmin):
    list_display = (
        "to_email",
        "template",
        "template_type",
        "subject",
        "status",
        "related_model",
        "related_object_id",
        "ses_message_id",
        "sent_at",
        "created_at",
    )
    list_filter = (
        "status",
        "template_type",
        "related_model",
        "sent_at",
        "created_at",
    )
    search_fields = (
        "to_email",
        "subject",
        "template__name",
        "template__slug",
        "ses_message_id",
        "error_message",
        "related_model",
        "related_object_id",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "sent_at",
    )
    autocomplete_fields = ("template",)


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "template",
        "target_type",
        "status",
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
    search_fields = (
        "name",
        "description",
        "template__name",
        "template__slug",
        "from_email",
        "reply_to",
    )
    readonly_fields = (
        "last_run_at",
        "total_sent",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "template",
    )
    inlines = (CampaignRecipientInline,)
    fieldsets = (
        ("Campaign Details", {
            "fields": (
                "owner",
                "name",
                "description",
                "template",
                "target_type",
                "status",
            )
        }),
        ("Sender", {
            "fields": (
                "from_email",
                "reply_to",
            )
        }),
        ("Schedule / Limits", {
            "fields": (
                "start_date",
                "start_time",
                "weekdays_only",
                "daily_limit",
                "delay_seconds",
            )
        }),
        ("Run Info", {
            "fields": (
                "last_run_at",
                "total_sent",
            )
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(CampaignRecipient)
class CampaignRecipientAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "campaign",
        "first_name",
        "last_name",
        "company",
        "status",
        "client_id",
        "contact_id",
        "sent_at",
        "created_at",
    )
    list_filter = (
        "status",
        "campaign",
        "sent_at",
        "created_at",
    )
    search_fields = (
        "email",
        "first_name",
        "last_name",
        "company",
        "campaign__name",
        "last_error",
    )
    readonly_fields = (
        "sent_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("campaign",)


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "type",
        "provider",
        "provider_template_name",
        "language_code",
        "category",
        "is_active",
        "is_default_for_type",
        "owner",
        "created_at",
    )
    list_filter = (
        "type",
        "provider",
        "language_code",
        "category",
        "is_active",
        "is_default_for_type",
        "created_at",
    )
    search_fields = (
        "name",
        "slug",
        "provider_template_name",
        "body_text",
        "header_text",
        "footer_text",
        "notes",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)
    prepopulated_fields = {
        "slug": ("name",),
    }
    fieldsets = (
        ("Template Details", {
            "fields": (
                "owner",
                "name",
                "slug",
                "type",
                "provider",
                "provider_template_name",
                "language_code",
                "category",
                "is_active",
                "is_default_for_type",
            )
        }),
        ("Preview Text", {
            "fields": (
                "header_text",
                "body_text",
                "footer_text",
            )
        }),
        ("Variables", {
            "fields": ("variable_order",)
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


@admin.register(WhatsAppSendLog)
class WhatsAppSendLogAdmin(admin.ModelAdmin):
    list_display = (
        "to_number",
        "template",
        "template_type",
        "provider",
        "status",
        "related_model",
        "related_object_id",
        "provider_message_id",
        "sent_at",
        "created_at",
    )
    list_filter = (
        "status",
        "provider",
        "template_type",
        "related_model",
        "sent_at",
        "created_at",
    )
    search_fields = (
        "to_number",
        "rendered_message",
        "template__name",
        "template__slug",
        "provider_message_id",
        "error_message",
        "related_model",
        "related_object_id",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "sent_at",
    )
    autocomplete_fields = ("template",)