
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction, IntegrityError
from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from common.models import TimeStamped, Owned
from crm.models import Client, Lead
from services.models import Service, Package


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


class Deal(TimeStamped, Owned):
    name = models.CharField(max_length=255)

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="deals",
        null=True,
        blank=True,
    )

    lead = models.ForeignKey(
        Lead,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deals",
    )

    stage = models.CharField(max_length=32, choices=DealStage.choices, default=DealStage.NEW)

    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_close_date = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    closed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.client})"

    def get_absolute_url(self):
        return reverse("sales:deal_detail", args=[self.pk])


class Proposal(TimeStamped, Owned):
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
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("deal", "version")

    def __str__(self):
        return f"Proposal #{self.version} - {self.deal}"

    def get_absolute_url(self):
        return reverse("sales:proposal_detail", args=[self.pk])

    def recalculate_totals(self, save=True):
        """
        Calculates proposal totals.

        subtotal = sum of item line totals
        discount = fixed amount
        tax = percentage applied after discount

        total = (subtotal - discount) + tax_amount
        """

        agg = self.items.aggregate(subtotal=Sum("line_total"))
        subtotal = agg["subtotal"] or Decimal("0.00")

        discount = self.discount or Decimal("0.00")
        tax_percentage = self.tax or Decimal("0.00")

        taxable_amount = subtotal - discount

        if taxable_amount < Decimal("0.00"):
            taxable_amount = Decimal("0.00")

        tax_amount = (taxable_amount * tax_percentage) / Decimal("100.00")

        self.subtotal = subtotal
        self.total = taxable_amount + tax_amount

        if save:
            self.save(update_fields=["subtotal", "total", "updated_at"])


class ProposalItem(models.Model):
    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.CASCADE,
        related_name="items",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_items",
    )

    package = models.ForeignKey(
        Package,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposal_items",
    )

    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.service and self.package:
            raise ValidationError("Select either Service or Package, not both.")
        if not self.service and not self.package:
            raise ValidationError("Please select a Service or Package.")

    def save(self, *args, **kwargs):
        if not self.description:
            self.description = self.service.name if self.service else self.package.name

        if not self.unit_price:
            self.unit_price = (
                self.service.base_price if self.service else self.package.total_price
            ) or Decimal("0.00")

        self.line_total = (self.unit_price or Decimal("0.00")) * (self.quantity or 0)

        super().save(*args, **kwargs)
        self.proposal.recalculate_totals(save=True)

    def delete(self, *args, **kwargs):
        proposal = self.proposal
        super().delete(*args, **kwargs)
        proposal.recalculate_totals(save=True)

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class Contract(TimeStamped, Owned):
    CODE_PREFIX = "CTR"
    CODE_PAD = 3

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="contracts",
    )

    proposal = models.ForeignKey(
        Proposal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contracts",
    )

    number = models.CharField(max_length=64, unique=True, editable=False, blank=True)

    status = models.CharField(
        max_length=32,
        choices=ContractStatus.choices,
        default=ContractStatus.DRAFT,
    )

    signed_date = models.DateField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    terms = models.TextField(blank=True)
    file = models.FileField(upload_to="contracts/", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Contract {self.number or '-'} - {self.deal}"

    def get_absolute_url(self):
        return reverse("sales:contract_detail", args=[self.pk])

    @classmethod
    def _generate_next_number(cls):
        last = cls.objects.filter(number__startswith=cls.CODE_PREFIX).order_by("-number").first()
        if last and last.number:
            try:
                number = int(last.number.replace(cls.CODE_PREFIX, ""))
            except ValueError:
                number = 0
        else:
            number = 0
        return f"{cls.CODE_PREFIX}{number + 1:0{cls.CODE_PAD}d}"

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.only("number").get(pk=self.pk)
            if old.number:
                self.number = old.number

        if self.number:
            return super().save(*args, **kwargs)

        for _ in range(10):
            self.number = self._generate_next_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.number = ""

        raise IntegrityError("Could not generate unique contract number.")

    @transaction.atomic
    def populate_from_proposal(self, proposal, clear_existing=False):
        if clear_existing:
            self.items.all().delete()

        if not self.proposal_id:
            self.proposal = proposal
            self.save(update_fields=["proposal", "updated_at"])

        for item in proposal.items.all():
            ContractItem.objects.create(
                contract=self,
                proposal_item=item,
                service=item.service,
                package=item.package,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )


class ContractItem(models.Model):
    contract = models.ForeignKey(
        Contract,
        on_delete=models.CASCADE,
        related_name="items",
    )

    proposal_item = models.ForeignKey(
        ProposalItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contract_items",
    )

    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)

    description = models.CharField(max_length=255, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def save(self, *args, **kwargs):
        if not self.description and self.proposal_item:
            self.description = self.proposal_item.description

        self.line_total = (self.unit_price or Decimal("0.00")) * (self.quantity or 0)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class Invoice(TimeStamped, Owned):
    CODE_PREFIX = "INV"
    CODE_PAD = 3

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="invoices",
    )

    contract = models.ForeignKey(
        Contract,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices",
    )

    number = models.CharField(max_length=64, unique=True, editable=False, blank=True)

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
        ordering = ["-issue_date"]

    def __str__(self):
        return f"Invoice {self.number or '-'}"

    def get_absolute_url(self):
        return reverse("sales:invoice_detail", args=[self.pk])

    @property
    def balance(self):
        return (self.total or Decimal("0.00")) - (self.amount_paid or Decimal("0.00"))

    @classmethod
    def _generate_next_number(cls):
        last = cls.objects.filter(number__startswith=cls.CODE_PREFIX).order_by("-number").first()
        if last and last.number:
            try:
                number = int(last.number.replace(cls.CODE_PREFIX, ""))
            except ValueError:
                number = 0
        else:
            number = 0
        return f"{cls.CODE_PREFIX}{number + 1:0{cls.CODE_PAD}d}"

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.only("number").get(pk=self.pk)
            if old.number:
                self.number = old.number

        if self.number:
            return super().save(*args, **kwargs)

        for _ in range(10):
            self.number = self._generate_next_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.number = ""

        raise IntegrityError("Could not generate unique invoice number.")

    def recalculate_totals(self, save=True):
        agg = self.items.aggregate(
            subtotal=Sum("line_subtotal"),
            tax=Sum("tax_amount"),
            total=Sum("line_total"),
        )

        self.subtotal = agg["subtotal"] or Decimal("0.00")
        self.tax = agg["tax"] or Decimal("0.00")
        self.total = agg["total"] or Decimal("0.00")

        if save:
            self.save(update_fields=["subtotal", "tax", "total", "updated_at"])

    @transaction.atomic
    def populate_from_contract(self, contract, clear_existing=False):
        if contract.deal_id != self.deal_id:
            raise ValidationError("Invoice deal must match contract deal.")

        self.contract = contract
        self.save(update_fields=["contract", "updated_at"])

        if clear_existing:
            self.items.all().delete()

        for item in contract.items.all():
            InvoiceItem.objects.create(
                invoice=self,
                contract_item=item,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                tax_rate=Decimal("0.00"),
            )

        self.recalculate_totals(save=True)


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
    )

    contract_item = models.ForeignKey(
        ContractItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_items",
    )

    description = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        ordering = ["id"]

    def clean(self):
        if self.invoice_id and self.invoice.status != InvoiceStatus.DRAFT:
            raise ValidationError("Cannot modify invoice items after invoice is issued.")

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.full_clean()

        base = (self.unit_price or Decimal("0.00")) * (self.quantity or 0)
        tax = (base * (self.tax_rate or Decimal("0.00"))) / Decimal("100.00")

        self.line_subtotal = base
        self.tax_amount = tax
        self.line_total = base + tax

        super().save(*args, **kwargs)
        self.invoice.recalculate_totals(save=True)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        if self.invoice_id and self.invoice.status != InvoiceStatus.DRAFT:
            raise ValidationError("Cannot delete invoice items after invoice is issued.")

        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.recalculate_totals(save=True)

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class Payment(TimeStamped, Owned):
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

    reference = models.CharField(max_length=128, blank=True)
    notes = models.TextField(blank=True)

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_received",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {self.amount} for {self.invoice}"

    def get_absolute_url(self):
        return reverse("sales:invoice_detail", args=[self.invoice_id])

    def clean(self):
        if not self.invoice_id or self.amount is None:
            return

        already_paid = (
            self.invoice.payments.exclude(pk=self.pk).aggregate(total=Sum("amount"))["total"]
            or Decimal("0.00")
        )

        remaining = (self.invoice.total or Decimal("0.00")) - already_paid

        if self.amount > remaining:
            raise ValidationError({"amount": f"Payment exceeds remaining balance ({remaining})."})

    def _update_invoice_amount_paid(self):
        invoice = self.invoice

        total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        invoice.amount_paid = total_paid

        if invoice.total and invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        elif invoice.status in [InvoiceStatus.PAID, InvoiceStatus.PARTIALLY_PAID]:
            invoice.status = InvoiceStatus.ISSUED

        invoice.save(update_fields=["amount_paid", "status", "updated_at"])

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        self._update_invoice_amount_paid()

    @transaction.atomic
    def delete(self, *args, **kwargs):
        invoice = self.invoice
        super().delete(*args, **kwargs)
        invoice.refresh_from_db()
        total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        invoice.amount_paid = total_paid

        if invoice.total and invoice.amount_paid >= invoice.total:
            invoice.status = InvoiceStatus.PAID
        elif invoice.amount_paid > 0:
            invoice.status = InvoiceStatus.PARTIALLY_PAID
        elif invoice.status in [InvoiceStatus.PAID, InvoiceStatus.PARTIALLY_PAID]:
            invoice.status = InvoiceStatus.ISSUED

        invoice.save(update_fields=["amount_paid", "status", "updated_at"])