# crm/admin.py

from django.contrib import admin

from .models import Client, Contact, Inquiry, Lead, Review


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 0
    fields = (
        "first_name",
        "last_name",
        "role",
        "email",
        "phone",
        "whatsapp",
        "is_primary",
        "allow_marketing",
    )
    readonly_fields = ()


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = (
        "rating",
        "title",
        "comment",
        "next_action",
        "next_action_date",
        "created_at",
    )
    readonly_fields = ("created_at",)


class InquiryInline(admin.TabularInline):
    model = Inquiry
    extra = 0
    fields = (
        "channel",
        "status",
        "name",
        "email",
        "phone",
        "whatsapp",
        "wedding_date",
        "handled_by",
        "lead",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("handled_by", "lead")


class LeadInline(admin.TabularInline):
    model = Lead
    extra = 0
    fields = (
        "name",
        "status",
        "source",
        "email",
        "phone",
        "whatsapp",
        "wedding_date",
        "budget_min",
        "budget_max",
        "created_at",
    )
    readonly_fields = ("created_at",)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_name",
        "email",
        "phone",
        "city",
        "district",
        "state",
        "country",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "is_active",
        "state",
        "country",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "name",
        "display_name",
        "email",
        "phone",
        "city",
        "district",
        "state",
        "country",
        "notes",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)
    inlines = (
        ContactInline,
        ReviewInline,
        InquiryInline,
        LeadInline,
    )
    fieldsets = (
        ("Basic Details", {
            "fields": (
                "owner",
                "name",
                "display_name",
                "email",
                "phone",
                "is_active",
            )
        }),
        ("Billing / Address", {
            "fields": (
                "billing_address",
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


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = (
        "first_name",
        "last_name",
        "client",
        "role",
        "email",
        "phone",
        "whatsapp",
        "is_primary",
        "allow_marketing",
        "owner",
        "created_at",
    )
    list_filter = (
        "role",
        "is_primary",
        "allow_marketing",
        "created_at",
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
        "phone",
        "whatsapp",
        "client__name",
        "client__display_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "client",
        "owner",
    )


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "channel",
        "status",
        "email",
        "phone",
        "whatsapp",
        "wedding_date",
        "wedding_city",
        "client",
        "lead",
        "handled_by",
        "owner",
        "created_at",
    )
    list_filter = (
        "channel",
        "status",
        "wedding_date",
        "wedding_state",
        "wedding_country",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "whatsapp",
        "message",
        "wedding_city",
        "wedding_district",
        "client__name",
        "client__display_name",
        "lead__name",
        "handled_by__username",
        "handled_by__first_name",
        "handled_by__last_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "client",
        "lead",
        "handled_by",
    )
    fieldsets = (
        ("Inquiry", {
            "fields": (
                "owner",
                "channel",
                "status",
                "handled_by",
                "client",
                "lead",
            )
        }),
        ("Contact Details", {
            "fields": (
                "name",
                "email",
                "phone",
                "whatsapp",
            )
        }),
        ("Wedding Details", {
            "fields": (
                "wedding_date",
                "wedding_city",
                "wedding_district",
                "wedding_state",
                "wedding_country",
            )
        }),
        ("Message", {
            "fields": ("message",)
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "status",
        "source",
        "email",
        "phone",
        "whatsapp",
        "wedding_date",
        "wedding_city",
        "budget_min",
        "budget_max",
        "client",
        "inquiry",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "source",
        "wedding_date",
        "wedding_state",
        "wedding_country",
        "next_action_date",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "whatsapp",
        "wedding_city",
        "wedding_district",
        "source_detail",
        "notes",
        "client__name",
        "client__display_name",
        "inquiry__name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "client",
        "inquiry",
    )
    fieldsets = (
        ("Lead", {
            "fields": (
                "owner",
                "inquiry",
                "client",
                "name",
                "status",
                "source",
                "source_detail",
            )
        }),
        ("Contact Details", {
            "fields": (
                "email",
                "phone",
                "whatsapp",
            )
        }),
        ("Wedding Details", {
            "fields": (
                "wedding_date",
                "wedding_city",
                "wedding_district",
                "wedding_state",
                "wedding_country",
            )
        }),
        ("Budget", {
            "fields": (
                "budget_min",
                "budget_max",
            )
        }),
        ("Next Action", {
            "fields": (
                "next_action_date",
                "next_action_note",
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


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "rating",
        "title",
        "next_action",
        "next_action_date",
        "owner",
        "created_at",
    )
    list_filter = (
        "rating",
        "next_action_date",
        "created_at",
    )
    search_fields = (
        "client__name",
        "client__display_name",
        "title",
        "comment",
        "next_action",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "client",
    )