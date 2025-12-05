# services/admin.py
from django.contrib import admin

from .models import (
    Vendor,
    Service,
    Package,
    PackageItem,
    InventoryItem,
)


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company_name",
        "vendor_type",
        "phone",
        "email",
        "city",
        "district",
        "state",
        "country",
        "is_preferred",
    )
    list_filter = (
        "vendor_type",
        "is_preferred",
        "city",
        "district",
        "state",
        "country",
    )
    search_fields = (
        "name",
        "company_name",
        "email",
        "phone",
        "city",
        "district",
        "state",
        "country",
    )
    raw_id_fields = ("owner",)


class PackageItemInline(admin.TabularInline):
    model = PackageItem
    extra = 1


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "category",
        "base_price",
        "is_active",
    )
    list_filter = ("category", "is_active")
    search_fields = ("name", "code", "description")
    filter_horizontal = ("vendors",)
    raw_id_fields = ("owner",)


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "total_price", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    inlines = [PackageItemInline]
    raw_id_fields = ("owner",)


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "sku",
        "service",
        "quantity_total",
        "quantity_available",
        "unit",
        "location",
    )
    list_filter = ("unit",)
    search_fields = ("name", "sku", "location")
    raw_id_fields = ("service", "owner")
