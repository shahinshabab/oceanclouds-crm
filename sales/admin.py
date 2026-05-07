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


class ProposalItemInline(admin.TabularInline):
    model = ProposalItem
    extra = 0
    fields = (
        "service",
        "package",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = (
        "service",
        "package",
    )


class ContractItemInline(admin.TabularInline):
    model = ContractItem
    extra = 0
    fields = (
        "proposal_item",
        "service",
        "package",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = (
        "proposal_item",
        "service",
        "package",
    )


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    fields = (
        "contract_item",
        "description",
        "quantity",
        "unit_price",
        "tax_rate",
        "line_subtotal",
        "tax_amount",
        "line_total",
    )
    readonly_fields = (
        "line_subtotal",
        "tax_amount",
        "line_total",
    )
    autocomplete_fields = ("contract_item",)


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    fields = (
        "date",
        "amount",
        "payment_type",
        "method",
        "reference",
        "received_by",
        "owner",
    )
    autocomplete_fields = (
        "received_by",
        "owner",
    )


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "lead",
        "stage",
        "amount",
        "expected_close_date",
        "is_active",
        "closed_on",
        "owner",
        "created_at",
    )
    list_filter = (
        "stage",
        "is_active",
        "expected_close_date",
        "closed_on",
        "created_at",
    )
    search_fields = (
        "name",
        "description",
        "client__name",
        "client__display_name",
        "lead__name",
        "lead__email",
        "lead__phone",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "client",
        "lead",
    )
    fieldsets = (
        ("Deal Details", {
            "fields": (
                "owner",
                "name",
                "client",
                "lead",
                "stage",
                "amount",
                "expected_close_date",
                "description",
                "is_active",
                "closed_on",
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


@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "deal",
        "version",
        "status",
        "valid_until",
        "subtotal",
        "discount",
        "tax",
        "total",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "valid_until",
        "created_at",
    )
    search_fields = (
        "title",
        "notes",
        "deal__name",
        "deal__client__name",
        "deal__client__display_name",
    )
    readonly_fields = (
        "subtotal",
        "total",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "deal",
    )
    inlines = (ProposalItemInline,)
    fieldsets = (
        ("Proposal Details", {
            "fields": (
                "owner",
                "deal",
                "title",
                "version",
                "status",
                "valid_until",
            )
        }),
        ("Totals", {
            "fields": (
                "subtotal",
                "discount",
                "tax",
                "total",
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


@admin.register(ProposalItem)
class ProposalItemAdmin(admin.ModelAdmin):
    list_display = (
        "proposal",
        "service",
        "package",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    list_filter = (
        "service",
        "package",
    )
    search_fields = (
        "proposal__title",
        "proposal__deal__name",
        "service__name",
        "service__code",
        "package__name",
        "package__code",
        "description",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = (
        "proposal",
        "service",
        "package",
    )


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "deal",
        "proposal",
        "status",
        "signed_date",
        "start_date",
        "end_date",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "signed_date",
        "start_date",
        "end_date",
        "created_at",
    )
    search_fields = (
        "number",
        "terms",
        "deal__name",
        "deal__client__name",
        "deal__client__display_name",
        "proposal__title",
    )
    readonly_fields = (
        "number",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "deal",
        "proposal",
    )
    inlines = (ContractItemInline,)
    fieldsets = (
        ("Contract Details", {
            "fields": (
                "owner",
                "deal",
                "proposal",
                "number",
                "status",
                "signed_date",
                "start_date",
                "end_date",
                "file",
            )
        }),
        ("Terms", {
            "fields": ("terms",)
        }),
        ("System Info", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )


@admin.register(ContractItem)
class ContractItemAdmin(admin.ModelAdmin):
    list_display = (
        "contract",
        "proposal_item",
        "service",
        "package",
        "description",
        "quantity",
        "unit_price",
        "line_total",
    )
    list_filter = (
        "service",
        "package",
    )
    search_fields = (
        "contract__number",
        "contract__deal__name",
        "proposal_item__description",
        "service__name",
        "package__name",
        "description",
    )
    readonly_fields = ("line_total",)
    autocomplete_fields = (
        "contract",
        "proposal_item",
        "service",
        "package",
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "number",
        "deal",
        "contract",
        "issue_date",
        "due_date",
        "status",
        "subtotal",
        "tax",
        "total",
        "amount_paid",
        "balance",
        "owner",
        "created_at",
    )
    list_filter = (
        "status",
        "issue_date",
        "due_date",
        "created_at",
    )
    search_fields = (
        "number",
        "notes",
        "deal__name",
        "deal__client__name",
        "deal__client__display_name",
        "contract__number",
    )
    readonly_fields = (
        "number",
        "subtotal",
        "tax",
        "total",
        "amount_paid",
        "balance",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "deal",
        "contract",
    )
    inlines = (
        InvoiceItemInline,
        PaymentInline,
    )
    fieldsets = (
        ("Invoice Details", {
            "fields": (
                "owner",
                "deal",
                "contract",
                "number",
                "issue_date",
                "due_date",
                "status",
            )
        }),
        ("Totals", {
            "fields": (
                "subtotal",
                "tax",
                "total",
                "amount_paid",
                "balance",
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


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "contract_item",
        "description",
        "quantity",
        "unit_price",
        "tax_rate",
        "line_subtotal",
        "tax_amount",
        "line_total",
    )
    search_fields = (
        "invoice__number",
        "invoice__deal__name",
        "contract_item__description",
        "description",
    )
    readonly_fields = (
        "line_subtotal",
        "tax_amount",
        "line_total",
    )
    autocomplete_fields = (
        "invoice",
        "contract_item",
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "date",
        "amount",
        "payment_type",
        "method",
        "reference",
        "received_by",
        "owner",
        "created_at",
    )
    list_filter = (
        "payment_type",
        "method",
        "date",
        "received_by",
        "created_at",
    )
    search_fields = (
        "invoice__number",
        "invoice__deal__name",
        "invoice__deal__client__name",
        "reference",
        "notes",
        "received_by__username",
        "received_by__first_name",
        "received_by__last_name",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
    )
    autocomplete_fields = (
        "owner",
        "invoice",
        "received_by",
    )