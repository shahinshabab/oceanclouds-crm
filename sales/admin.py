# sales/admin.py
from django.contrib import admin

from .models import (
    Deal,
    Proposal,
    ProposalItem,
    Contract,
    ContractItem,
    Invoice,
    InvoiceItem,
    Payment,
)


# ---------------------------------------------------------
# Deal
# ---------------------------------------------------------
@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "stage",
        "amount",
        "expected_close_date",
        "is_active",
        "owner",
        "created_at",
    )
    list_filter = ("stage", "is_active", "created_at")
    search_fields = (
        "name",
        "client__name",
    )
    raw_id_fields = ("client", "owner")


# ---------------------------------------------------------
# Proposal
# ---------------------------------------------------------
class ProposalItemInline(admin.TabularInline):
    model = ProposalItem
    extra = 1


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ("deal", "title", "version", "status", "valid_until", "total")
    list_filter = ("status",)
    search_fields = ("deal__name", "title")
    inlines = [ProposalItemInline]
    raw_id_fields = ("deal", "owner")


# ---------------------------------------------------------
# Contract
# ---------------------------------------------------------
class ContractItemInline(admin.TabularInline):
    model = ContractItem
    extra = 1


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    readonly_fields = ("number", "created_at", "updated_at")
    list_display = ("number", "deal", "status", "signed_date", "start_date", "end_date")
    list_filter = ("status",)
    search_fields = ("number", "deal__name")
    raw_id_fields = ("deal", "proposal", "owner")
    inlines = [ContractItemInline]


# ---------------------------------------------------------
# Invoice
# ---------------------------------------------------------
class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    readonly_fields = ("number", "created_at", "updated_at")
    list_display = (
        "number",
        "deal_client",
        "deal",
        "issue_date",
        "due_date",
        "status",
        "total",
        "amount_paid",
        "balance",
    )
    list_filter = ("status", "issue_date")
    search_fields = (
        "number",
        "deal__name",
        "deal__client__name",
    )
    inlines = [InvoiceItemInline, PaymentInline]
    raw_id_fields = ("deal", "owner")

    def deal_client(self, obj):
        return obj.deal.client if obj.deal_id else None

    deal_client.short_description = "Client"


# ---------------------------------------------------------
# Payment
# ---------------------------------------------------------
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("invoice", "date", "amount", "method", "payment_type", "received_by")
    list_filter = ("method", "payment_type", "date")
    search_fields = ("invoice__number", "reference")
    raw_id_fields = ("invoice", "received_by", "owner")
