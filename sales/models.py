# sales/models.py
from django.conf import settings
from django.db import models, transaction
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from common.models import TimeStamped, Owned
from crm.models import Client
from services.models import Service, Package

from django.core.exceptions import ValidationError
from django.db.models import Sum


# -------------------------------------------------------------------
# Choice Enums
# -------------------------------------------------------------------

class DealStage(models.TextChoices):
    NEW = "new", _("New")
    QUALIFIED = "qualified", _("Qualified")
    PROPOSAL_SENT = "proposal_sent", _("Proposal Sent")
    NEGOTIATION = "negotiation", _("Negotiation")
    WON = "won", _("Won")
    LOST = "lost", _("Lost")
    ON_HOLD = "on_hold", _("On Hold")


class ProposalStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SENT = "sent", _("Sent")
    ACCEPTED = "accepted", _("Accepted")
    REJECTED = "rejected", _("Rejected")
    EXPIRED = "expired", _("Expired")


class ContractStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    PENDING_SIGNATURE = "pending_signature", _("Pending Signature")
    SIGNED = "signed", _("Signed")
    CANCELLED = "cancelled", _("Cancelled")


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ISSUED = "issued", _("Issued")
    PARTIALLY_PAID = "partially_paid", _("Partially Paid")
    PAID = "paid", _("Paid")
    OVERDUE = "overdue", _("Overdue")
    CANCELLED = "cancelled", _("Cancelled")


class PaymentMethod(models.TextChoices):
    CASH = "cash", _("Cash")
    CARD = "card", _("Card")
    UPI = "upi", _("UPI")
    BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
    ONLINE = "online", _("Online Gateway")
    CHEQUE = "cheque", _("Cheque")


class PaymentType(models.TextChoices):
    ADVANCE = "advance", _("Advance")
    INSTALLMENT = "installment", _("Installment / Partial")
    FINAL = "final", _("Final")
    REFUND = "refund", _("Refund")
    OTHER = "other", _("Other")


# -------------------------------------------------------------------
# Deal
# -------------------------------------------------------------------

class Deal(TimeStamped, Owned):
    """
    Sales opportunity / booking pipeline item.
    """

    name = models.CharField(max_length=255)

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    stage = models.CharField(
        max_length=32,
        choices=DealStage.choices,
        default=DealStage.NEW,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Expected deal value (optional)."),
    )

    expected_close_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    closed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.name} ({self.client})"

    def get_absolute_url(self):
        return reverse("sales:deal_detail", args=[self.pk])


# -------------------------------------------------------------------
# Proposal & ProposalItem
# -------------------------------------------------------------------

class Proposal(TimeStamped, Owned):
    """
    Quote sent to client for a given deal.
    """

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="proposals",
    )
    title = models.CharField(max_length=255)
    version = models.PositiveIntegerField(default=1)

    status = models.CharField(
        max_length=32,
        choices=ProposalStatus.choices,
        default=ProposalStatus.DRAFT,
    )
    valid_until = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True,
        help_text=_("Flat discount amount."),
    )
    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        blank=True,
        help_text=_("Total tax amount (currently unused; set to 0)."),
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("deal", "version")

    def __str__(self) -> str:
        return f"Proposal #{self.version} for {self.deal}"

    def get_absolute_url(self):
        return reverse("sales:proposal_detail", args=[self.pk])


class ProposalItem(models.Model):
    """
    Line item in a proposal. Can be a single Service OR a Package.
    """

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="items",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="proposal_items",
        null=True,
        blank=True,
    )
    # Allow linking to a Package instead of a Service
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        related_name="proposal_items",
        null=True,
        blank=True,
    )
    description = models.CharField(
        max_length=255,
        blank=True,  # allow auto-fill
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.description} x {self.quantity}"

    def clean(self):
        """
        Ensure user picks either a service or a package (not both, not none).
        """
        super().clean()
        if not self.service and not self.package:
            raise ValidationError("Please select a Service or a Package.")
        if self.service and self.package:
            raise ValidationError("Select either Service OR Package, not both.")

    def save(self, *args, **kwargs):
        # Auto description if not set
        if not self.description:
            if self.service:
                self.description = self.service.name
            elif self.package:
                self.description = self.package.name

        # Auto unit_price if zero and something is linked
        if (self.unit_price is None or self.unit_price == 0):
            if self.service:
                self.unit_price = self.service.base_price or 0
            elif self.package:
                self.unit_price = self.package.total_price or 0

        self.line_total = (self.unit_price or 0) * (self.quantity or 0)
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Contract & ContractItem
# -------------------------------------------------------------------

class Contract(TimeStamped, Owned):
    """
    Signed agreement based on a proposal/deal.
    Contract items are duplicated from ProposalItems so the contract
    remains valid even if proposals are later deleted.
    """

    CODE_PREFIX = "CTR"
    CODE_PAD = 3   # CTR001, CTR002...

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="contracts",
    )

    # Optional: which proposal this contract came from
    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.SET_NULL,
        related_name="contracts",
        null=True,
        blank=True,
    )

    number = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        help_text=_("Internal contract number (auto-generated if left blank, e.g., CTR001)."),
    )

    status = models.CharField(
        max_length=32,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
    )
    signed_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)

    # Optional uploaded contract file
    file = models.FileField(
        upload_to="contracts/",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Contract {self.number or '—'} - {self.deal}"

    def get_absolute_url(self):
        return reverse("sales:contract_detail", args=[self.pk])

    # ---------- Code generation ---------- #
    @classmethod
    def _generate_next_number(cls) -> str:
        """
        Generate the next sequential contract number like CTR001, CTR002, ...
        Looks at the highest existing number starting with the prefix.
        """
        prefix = cls.CODE_PREFIX
        pad = cls.CODE_PAD

        last = (
            cls.objects
            .filter(number__startswith=prefix)
            .order_by("-number")
            .only("number")
            .first()
        )

        if last and last.number:
            suffix = last.number.replace(prefix, "")
            try:
                number = int(suffix)
            except ValueError:
                number = 0
        else:
            number = 0

        return f"{prefix}{number + 1:0{pad}d}"

    def save(self, *args, **kwargs):
        # Only auto-generate if no number provided
        if not self.number:
            self.number = self._generate_next_number()
        super().save(*args, **kwargs)

    # ---------- Helper to populate from proposal ---------- #
    @transaction.atomic
    def populate_from_proposal(self, proposal: Proposal, clear_existing: bool = False):
        """
        Duplicate all ProposalItems into ContractItems.
        """
        # No need for local import, ContractItem is in the same file
        if clear_existing:
            self.items.all().delete()

        # Remember where it came from
        if not self.proposal_id:
            self.proposal = proposal
            self.save(update_fields=["proposal"])

        for pitem in proposal.items.all():
            ContractItem.objects.create(
                contract=self,
                proposal_item=pitem,
                service=pitem.service,
                package=pitem.package,
                description=pitem.description,
                quantity=pitem.quantity,
                unit_price=pitem.unit_price,
            )


class ContractItem(models.Model):
    """
    Line item inside a contract, usually copied from a ProposalItem.
    """

    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="items",
    )
    # Optional: remember which proposal line this came from
    proposal_item = models.ForeignKey(
        ProposalItem,
        on_delete=models.SET_NULL,
        related_name="contract_items",
        null=True,
        blank=True,
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="contract_items",
        null=True,
        blank=True,
    )
    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        related_name="contract_items",
        null=True,
        blank=True,
    )

    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.description} x {self.quantity}"

    def clean(self):
        super().clean()
        if not self.service and not self.package:
            # This is allowed if the description is manually maintained,
            # but if you want to enforce Service/Package, uncomment:
            # raise ValidationError("Please select a Service or a Package.")
            pass

    def save(self, *args, **kwargs):
        # Default description if empty
        if not self.description:
            if self.service:
                self.description = self.service.name
            elif self.package:
                self.description = self.package.name
            elif self.proposal_item:
                self.description = self.proposal_item.description

        if (self.unit_price is None or self.unit_price == 0):
            if self.service:
                self.unit_price = self.service.base_price or 0
            elif self.package:
                self.unit_price = self.package.total_price or 0
            elif self.proposal_item:
                self.unit_price = self.proposal_item.unit_price or 0

        self.line_total = (self.unit_price or 0) * (self.quantity or 0)
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Invoice & InvoiceItem
# -------------------------------------------------------------------
class Invoice(TimeStamped, Owned):
    """
    Billing document with itemized charges.
    """

    CODE_PREFIX = "INV"
    CODE_PAD = 3  # INV001, INV002...

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    number = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        help_text=_("Invoice number (auto-generated if blank)."),
    )

    issue_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=32,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("-issue_date",)

    def __str__(self):
        return f"Invoice {self.number}"

    def get_absolute_url(self):
        return reverse("sales:invoice_detail", args=[self.pk])

    # -----------------------------------------------------------
    # Auto invoice code generator (INV001, INV002...)
    # -----------------------------------------------------------
    @classmethod
    def _generate_next_number(cls) -> str:
        prefix = cls.CODE_PREFIX
        pad = cls.CODE_PAD

        last = (
            cls.objects.filter(number__startswith=prefix)
            .order_by("-number")
            .only("number")
            .first()
        )

        if last and last.number:
            suffix = last.number.replace(prefix, "")
            try:
                number = int(suffix)
            except ValueError:
                number = 0
        else:
            number = 0

        return f"{prefix}{number + 1:0{pad}d}"

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = self._generate_next_number()
        super().save(*args, **kwargs)

    # -----------------------------------------------------------
    # Computations
    # -----------------------------------------------------------
    @property
    def balance(self):
        return (self.total or 0) - (self.amount_paid or 0)

    def recalculate_totals(self, save=True):
        agg = self.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or 0
        self.subtotal = subtotal
        self.tax = 0
        self.total = subtotal

        if save:
            self.save(update_fields=["subtotal", "tax", "total", "updated_at"])

    def populate_from_contract(self, contract, clear_existing=False):
        """
        Copy Contract Items → Invoice Items.
        """

        if clear_existing:
            self.items.all().delete()

        for citem in contract.items.all():
            InvoiceItem.objects.create(
                invoice=self,
                contract_item=citem,          # 👈 IMPORTANT
                description=citem.description,
                quantity=citem.quantity,
                unit_price=citem.unit_price,
                tax_rate=0,
            )

        self.recalculate_totals(save=True)




class InvoiceItem(models.Model):
    """
    Line item in an invoice. Usually copied from ContractItem.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )
    contract_item = models.ForeignKey(
        ContractItem,
        on_delete=models.SET_NULL,
        related_name="invoice_items",
        null=True,
        blank=True,
    )

    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        blank=True,
        help_text=_("Tax rate as percentage, e.g. 5.00 (0 for now)."),
    )
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.description} x {self.quantity}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        base_total = (self.unit_price or 0) * (self.quantity or 0)
        tax_amount = base_total * (self.tax_rate or 0) / 100
        self.line_total = base_total + tax_amount

        super().save(*args, **kwargs)

        # Recalculate parent invoice totals any time an item is saved
        if self.invoice_id:
            self.invoice.recalculate_totals(save=True)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)

        # Recalculate after deletion
        if invoice.pk:
            invoice.recalculate_totals(save=True)


# -------------------------------------------------------------------
# Payment
# -------------------------------------------------------------------

class Payment(TimeStamped, Owned):
    """
    Incoming payment against an invoice.
    """

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)

    payment_type = models.CharField(
        max_length=32,
        choices=PaymentType.choices,
        default=PaymentType.ADVANCE,
    )

    method = models.CharField(
        max_length=32,
        choices=PaymentMethod.choices,
        default=PaymentMethod.UPI,
    )
    reference = models.CharField(
        max_length=128,
        blank=True,
        help_text=_("Transaction reference, cheque no., etc."),
    )
    notes = models.TextField(blank=True)

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="payments_received",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"Payment {self.amount} for {self.invoice}"

    def get_absolute_url(self):
        return reverse("sales:invoice_detail", args=[self.invoice_id])

    # ---------- VALIDATION: don't allow overpayment ---------- #
    def clean(self):
        super().clean()

        if not self.invoice or self.amount is None:
            return

        already_paid = (
            self.invoice.payments
            .exclude(pk=self.pk)  # exclude self when editing
            .aggregate(total=Sum("amount"))["total"]
            or 0
        )

        invoice_total = self.invoice.total or 0
        remaining = invoice_total - already_paid

        if self.amount > remaining:
            raise ValidationError({
                "amount": f"Payment exceeds remaining balance ({remaining})."
            })

    # ---------- Helper to update invoice totals/status ---------- #
    def _update_invoice_amount_paid(self):
        """
        Recalculate invoice.amount_paid from all payments
        and adjust invoice.status if you want.
        """
        invoice = self.invoice

        total_paid = (
            invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
        )
        invoice.amount_paid = total_paid

        # Optional: update status based on payment progress
        if invoice.total and invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0 and invoice.amount_paid < invoice.total:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        # else: leave status as is (DRAFT/ISSUED/etc.)

        invoice.save(update_fields=["amount_paid", "status", "updated_at"])

    # ---------- Override save & delete ---------- #
    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Validate, save payment, then update related invoice totals.
        """
        self.full_clean()  # runs clean() + field validation
        super().save(*args, **kwargs)
        self._update_invoice_amount_paid()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """
        Ensure invoice totals are updated when a payment is deleted.
        """
        invoice = self.invoice
        super().delete(*args, **kwargs)

        # re-fetch invoice to be safe
        invoice.refresh_from_db()
        total_paid = (
            invoice.payments.aggregate(total=Sum("amount"))["total"] or 0
        )
        invoice.amount_paid = total_paid

        if invoice.total and invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0 and invoice.amount_paid < invoice.total:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        else:
            # you can choose to reset back to ISSUED, etc., if you like
            pass

        invoice.save(update_fields=["amount_paid", "status", "updated_at"])
