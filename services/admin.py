# services/admin.py

from django.contrib import admin

from .models import Vendor, Service, Package, PackageItem, InventoryItem


class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 0
    fields = (
        "service",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = ("service",)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company_name",
        "vendor_type",
        "email",
        "phone",
        "whatsapp",
        "city",
        "district",
        "is_preferred",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "vendor_type",
        "is_preferred",
        "is_active",
        "state",
        "country",
        "created_at",
    )
    search_fields = (
        "name",
        "company_name",
        "email",
        "phone",
        "alt_phone",
        "whatsapp",
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
        ("Vendor Details", {
            "fields": (
                "owner",
                "name",
                "company_name",
                "vendor_type",
                "is_preferred",
                "is_active",
            )
        }),
        ("Contact", {
            "fields": (
                "email",
                "phone",
                "alt_phone",
                "whatsapp",
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


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "category",
        "base_price",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "category",
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "code",
        "description",
        "notes",
        "vendors__name",
        "vendors__company_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "vendors",
    )
    filter_horizontal = ("vendors",)
    fieldsets = (
        ("Service Details", {
            "fields": (
                "owner",
                "name",
                "code",
                "category",
                "description",
                "base_price",
                "vendors",
                "is_active",
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


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "total_price",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "is_active",
        "created_at",
    )
    search_fields = (
        "name",
        "code",
        "description",
        "notes",
    )
    readonly_fields = (
        "total_price",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("owner",)
    inlines = (PackageItemInline,)
    fieldsets = (
        ("Package Details", {
            "fields": (
                "owner",
                "name",
                "code",
                "description",
                "total_price",
                "is_active",
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


@admin.register(PackageItem)
class PackageItemAdmin(admin.ModelAdmin):
    list_display = (
        "package",
        "service",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    list_filter = (
        "package",
        "service",
    )
    search_fields = (
        "package__name",
        "package__code",
        "service__name",
        "service__code",
        "description",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = (
        "package",
        "service",
    )


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "category",
        "service",
        "quantity_total",
        "quantity_available",
        "unit",
        "location",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = (
        "category",
        "is_active",
        "service",
        "created_at",
    )
    search_fields = (
        "name",
        "sku",
        "location",
        "notes",
        "service__name",
        "service__code",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "service",
    )