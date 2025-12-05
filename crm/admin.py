from django.contrib import admin

from .models import Client, Contact, Lead, Inquiry


class ContactInline(admin.TabularInline):
    model = Contact
    extra = 1
    fields = (
        "first_name",
        "last_name",
        "role",
        "email",
        "phone",
        "whatsapp",
        "is_primary",
    )
    show_change_link = True


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "display_name",
        "phone",
        "email",
        "city",
        "district",
        "state",
        "country",
        "instagram_handle",
        "is_active",
    )
    search_fields = (
        "name",
        "display_name",
        "email",
        "phone",
        "city",
        "district",
        "state",
        "instagram_handle",
    )
    list_filter = ("is_active", "city", "district", "state", "country")
    inlines = [ContactInline]


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
    list_filter = ("role", "is_primary")
    autocomplete_fields = ("client",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "whatsapp",
        "status",
        "source",
        "source_detail",
        "wedding_date",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
        "budget_min",
        "budget_max",
        "client",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "whatsapp",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
        "source",
        "source_detail",
        "client__name",
        "client__display_name",
    )
    list_filter = (
        "status",
        "source",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("client",)


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "channel",
        "status",
        "name",
        "email",
        "phone",
        "wedding_date",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
        "lead",
        "client",
        "handled_by",
        "created_at",
    )
    search_fields = (
        "name",
        "email",
        "phone",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
        "message",
        "lead__name",
        "client__name",
        "client__display_name",
    )
    list_filter = (
        "channel",
        "status",
        "handled_by",
        "wedding_city",
        "wedding_district",
        "wedding_state",
        "wedding_country",
    )
    date_hierarchy = "created_at"
    autocomplete_fields = ("lead", "client", "handled_by")
