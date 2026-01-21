# sales/views.py
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)
import json
from django.utils.safestring import mark_safe
from crm.models import Client
from common.mixins import AdminManagerMixin  # 👈 your roles mixin
from .forms import get_catalog_choices
from datetime import date, timedelta

from django.utils import timezone

from .models import (
    Deal,
    Proposal,
    Contract,
    Invoice,
    Payment,
    DealStage,
    ProposalStatus,
    ContractStatus,
    InvoiceStatus,
    PaymentMethod,
    PaymentType,
)
from .forms import (
    DealForm,
    ProposalForm,
    ProposalItemFormSet,
    ContractForm,
    InvoiceForm,
    PaymentForm,
)

from decimal import Decimal
from services.models import Service, Package

from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.views import View

from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from messaging.utils import send_templated_email
from messaging.models import EmailTemplate


# Optional: HTML-to-PDF with WeasyPrint (you need to install it)
try:
    from weasyprint import HTML
except ImportError:  # pragma: no cover - safe fallback
    HTML = None


# ============================================================================
# Deals
# ============================================================================

class DealListView(AdminManagerMixin, ListView):
    model = Deal
    template_name = "sales/deal_list.html"
    context_object_name = "deals"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("client")
        )

        request = self.request
        q = request.GET.get("q")
        stage = request.GET.get("stage")
        is_active = request.GET.get("is_active")

        # Search: deal name + client name
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(client__name__icontains=q)
            )

        # Filter: Stage
        if stage:
            qs = qs.filter(stage=stage)

        # Filter: Active / Inactive
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        context["q"] = request.GET.get("q", "")
        context["filter_stage"] = request.GET.get("stage", "")
        context["filter_is_active"] = request.GET.get("is_active", "")

        context["stage_choices"] = DealStage.choices
        context["is_active_choices"] = [
            ("", "All"),
            ("true", "Active only"),
            ("false", "Inactive only"),
        ]
        return context


class DealDetailView(AdminManagerMixin, DetailView):
    model = Deal
    template_name = "sales/deal_detail.html"
    context_object_name = "deal"


class DealCreateView(AdminManagerMixin, CreateView):
    model = Deal
    form_class = DealForm
    template_name = "sales/deal_form.html"
    success_url = reverse_lazy("sales:deal_list")

    def form_valid(self, form):
        # set deal owner
        form.instance.owner = self.request.user
        return super().form_valid(form)


class DealUpdateView(AdminManagerMixin, UpdateView):
    model = Deal
    form_class = DealForm
    template_name = "sales:deal_form.html"
    success_url = reverse_lazy("sales:deal_list")


# ============================================================================
# Proposals
# ============================================================================

def _get_price_maps():
    services_price_map = {
        str(s.id): str(s.base_price or Decimal("0.00"))
        for s in Service.objects.all().only("id", "base_price").order_by("id")
    }
    packages_price_map = {
        str(p.id): str(p.total_price or Decimal("0.00"))
        for p in Package.objects.all().only("id", "total_price").order_by("id")
    }
    return services_price_map, packages_price_map

class ProposalListView(AdminManagerMixin, ListView):
    model = Proposal
    template_name = "sales/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("deal", "deal__client")
        )

        request = self.request
        q = request.GET.get("q")
        status = request.GET.get("status")
        deal_stage = request.GET.get("deal_stage")

        # Search: deal name + proposal title
        if q:
            qs = qs.filter(
                Q(deal__name__icontains=q)
                | Q(title__icontains=q)
            )

        # Filter: Proposal status
        if status:
            qs = qs.filter(status=status)

        # Filter: Deal stage
        if deal_stage:
            qs = qs.filter(deal__stage=deal_stage)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        context["q"] = request.GET.get("q", "")
        context["filter_status"] = request.GET.get("status", "")
        context["filter_deal_stage"] = request.GET.get("deal_stage", "")

        context["status_choices"] = ProposalStatus.choices
        context["deal_stage_choices"] = DealStage.choices
        return context


class ProposalDetailView(AdminManagerMixin, DetailView):
    model = Proposal
    template_name = "sales/proposal_detail.html"
    context_object_name = "proposal"


class ProposalCreateView(AdminManagerMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "sales/proposal_form.html"
    success_url = reverse_lazy("sales:proposal_list")

    def get_initial(self):
        initial = super().get_initial()
        deal_id = self.request.GET.get("deal")
        if deal_id:
            initial["deal"] = deal_id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        services_price_map, packages_price_map = _get_price_maps()
        context["services_price_map_json"] = mark_safe(json.dumps(services_price_map))
        context["packages_price_map_json"] = mark_safe(json.dumps(packages_price_map))

        catalog_choices = get_catalog_choices()

        if self.request.method == "POST":
            proposal_instance = getattr(context.get("form"), "instance", None)
            context["item_formset"] = ProposalItemFormSet(
                self.request.POST,
                instance=proposal_instance,
                catalog_choices=catalog_choices,
            )
        else:
            context["item_formset"] = ProposalItemFormSet(
                catalog_choices=catalog_choices
            )

        return context


    def form_valid(self, form):
        form.instance.owner = self.request.user

        context = self.get_context_data(form=form)
        item_formset = context["item_formset"]

        if not item_formset.is_valid():
            return self.render_to_response(context)

        self.object = form.save()

        item_formset.instance = self.object
        item_formset.save()

        # ✅ Always compute totals from items
        self.object.recalculate_totals(save=True)

        return super().form_valid(form)



class ProposalUpdateView(AdminManagerMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "sales/proposal_form.html"
    success_url = reverse_lazy("sales:proposal_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        services_price_map, packages_price_map = _get_price_maps()
        context["services_price_map_json"] = mark_safe(json.dumps(services_price_map))
        context["packages_price_map_json"] = mark_safe(json.dumps(packages_price_map))

        catalog_choices = get_catalog_choices()

        proposal = self.object
        if self.request.method == "POST":
            context["item_formset"] = ProposalItemFormSet(
                self.request.POST,
                instance=proposal,
                catalog_choices=catalog_choices,
            )
        else:
            context["item_formset"] = ProposalItemFormSet(
                instance=proposal,
                catalog_choices=catalog_choices,
            )

        return context


    def form_valid(self, form):
        context = self.get_context_data(form=form)
        item_formset = context["item_formset"]

        if not item_formset.is_valid():
            return self.render_to_response(context)

        self.object = form.save()

        item_formset.instance = self.object
        item_formset.save()

        # ✅ Always compute totals from items
        self.object.recalculate_totals(save=True)

        return super().form_valid(form)



# ============================================================================
# Contracts
# ============================================================================

class ContractListView(AdminManagerMixin, ListView):
    model = Contract
    template_name = "sales/contract_list.html"
    context_object_name = "contracts"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("deal", "proposal", "deal__client")
        )

        request = self.request
        q = request.GET.get("q")
        status = request.GET.get("status")
        deal_stage = request.GET.get("deal_stage")

        # Search: contract number + deal name
        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(deal__name__icontains=q)
            )

        # Filter: Contract status
        if status:
            qs = qs.filter(status=status)

        # Filter: Deal stage
        if deal_stage:
            qs = qs.filter(deal__stage=deal_stage)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        context["q"] = request.GET.get("q", "")
        context["filter_status"] = request.GET.get("status", "")
        context["filter_deal_stage"] = request.GET.get("deal_stage", "")

        context["status_choices"] = ContractStatus.choices
        context["deal_stage_choices"] = DealStage.choices
        return context


class ContractDetailView(AdminManagerMixin, DetailView):
    model = Contract
    template_name = "sales/contract_detail.html"
    context_object_name = "contract"


class ContractCreateView(AdminManagerMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = "sales/contract_form.html"
    success_url = reverse_lazy("sales:contract_list")

    def get_initial(self):
        initial = super().get_initial()
        deal_id = self.request.GET.get("deal")
        proposal_id = self.request.GET.get("proposal")
        if deal_id:
            initial["deal"] = deal_id
        if proposal_id:
            initial["proposal"] = proposal_id
        return initial

    def form_valid(self, form):
        # 1) set owner
        form.instance.owner = self.request.user

        # 2) save contract first
        response = super().form_valid(form)
        contract = self.object

        # 3) if a proposal is linked, copy items from it
        if contract.proposal_id:
            contract.populate_from_proposal(contract.proposal, clear_existing=True)

        return response


class ContractUpdateView(AdminManagerMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = "sales/contract_form.html"
    success_url = reverse_lazy("sales:contract_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        contract = self.object

        # Optional: if proposal is set and you want to refresh items
        if contract.proposal_id and not contract.items.exists():
            contract.populate_from_proposal(contract.proposal, clear_existing=True)

        return response



# ============================================================================
# Invoices
# ============================================================================

class InvoiceListView(AdminManagerMixin, ListView):
    model = Invoice
    template_name = "sales/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def _get_period_dates(self, period_key: str):
        """
        Returns (start_date, end_date) inclusive, or (None, None) if no period filter.
        """
        today = timezone.localdate()

        if period_key == "this_month":
            start = today.replace(day=1)
            end = today
            return start, end

        if period_key == "last_month":
            first_this = today.replace(day=1)
            last_prev = first_this - timedelta(days=1)
            start_prev = last_prev.replace(day=1)
            return start_prev, last_prev

        if period_key == "last_3_months":
            # From first day of the month 2 months ago up to today
            first_this = today.replace(day=1)
            approx = first_this - timedelta(days=62)  # safely reaches ~2 months back
            start = approx.replace(day=1)
            end = today
            return start, end

        if period_key == "last_year":
            # previous calendar year: Jan 1 .. Dec 31 of last year
            start = date(today.year - 1, 1, 1)
            end = date(today.year - 1, 12, 31)
            return start, end

        return None, None

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("deal", "deal__client")
        )

        request = self.request
        q = (request.GET.get("q") or "").strip()
        status = (request.GET.get("status") or "").strip()
        period = (request.GET.get("period") or "").strip()  # ✅ new

        # Search: invoice number + client name
        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(deal__client__name__icontains=q)
            )

        # Filter: status
        if status:
            qs = qs.filter(status=status)

        # ✅ Filter: period (issue_date)
        start_date, end_date = self._get_period_dates(period)
        if start_date and end_date:
            qs = qs.filter(issue_date__gte=start_date, issue_date__lte=end_date)

        return qs.order_by("-issue_date", "-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        context["q"] = request.GET.get("q", "")
        context["filter_status"] = request.GET.get("status", "")
        context["filter_period"] = request.GET.get("period", "")  # ✅

        context["status_choices"] = InvoiceStatus.choices

        # ✅ dropdown options
        context["period_choices"] = [
            ("", "All periods"),
            ("this_month", "This month"),
            ("last_month", "Last month"),
            ("last_3_months", "Last 3 months"),
            ("last_year", "Last year"),
        ]
        return context



class InvoiceDetailView(AdminManagerMixin, DetailView):
    model = Invoice
    template_name = "sales/invoice_detail.html"
    context_object_name = "invoice"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.object

        # URL for the "Download PDF" button
        context["pdf_download_url"] = reverse(
            "sales:invoice_download",
            args=[invoice.pk],
        )
        return context


class InvoiceCreateView(AdminManagerMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"
    success_url = reverse_lazy("sales:invoice_list")

    def get_initial(self):
        initial = super().get_initial()
        deal_id = self.request.GET.get("deal")
        if deal_id:
            initial["deal"] = deal_id
        return initial

    def _get_contract_for_invoice(self, invoice):
        """
        Resolve which contract to use:
        1) contract_id from POST (hidden field) or GET
        2) fallback: latest contract for this deal (optionally only SIGNED)
        """
        contract = None

        contract_id = (
            self.request.POST.get("contract_id")
            or self.request.GET.get("contract")
        )

        if contract_id:
            try:
                contract = Contract.objects.get(
                    pk=contract_id,
                    deal=invoice.deal,
                )
            except Contract.DoesNotExist:
                contract = None

        if contract is None:
            # If you really want only signed contracts, keep the filter:
            # qs = invoice.deal.contracts.filter(status=ContractStatus.SIGNED)
            qs = invoice.deal.contracts.all()  # 👈 less strict, uses latest contract
            contract = qs.order_by("-signed_date", "-created_at").first()

        return contract

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)

        invoice = self.object
        contract = self._get_contract_for_invoice(invoice)

        if contract:
            invoice.populate_from_contract(contract, clear_existing=True)

        return response



class InvoiceUpdateView(AdminManagerMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"
    success_url = reverse_lazy("sales:invoice_list")


# ============================================================================
# Invoice PDF Download
# ============================================================================

class InvoicePDFDownloadView(AdminManagerMixin, DetailView):
    """
    Generates a PDF from the invoice HTML template and returns it as a download.

    Template to use for PDF: 'sales/invoice_pdf.html'
    """
    model = Invoice

    def get(self, request, *args, **kwargs):
        if HTML is None:
            # WeasyPrint not installed – fail gracefully
            raise Http404("PDF generation is not available. Install WeasyPrint.")

        invoice = self.get_object()

        html_string = render_to_string(
            "sales/invoice_pdf.html",
            {"invoice": invoice},
            request=request,
        )

        pdf_file = HTML(
            string=html_string,
            base_url=request.build_absolute_uri(),
        ).write_pdf()

        filename = f"invoice_{invoice.number or invoice.pk}.pdf"

        response = HttpResponse(pdf_file, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# ============================================================================
# Payments
# ============================================================================

class PaymentListView(AdminManagerMixin, ListView):
    model = Payment
    template_name = "sales/payment_list.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("invoice", "invoice__deal", "invoice__deal__client")
        )

        request = self.request
        q = request.GET.get("q")
        method = request.GET.get("method")
        payment_type = request.GET.get("payment_type")

        # Search: invoice number + reference
        if q:
            qs = qs.filter(
                Q(invoice__number__icontains=q)
                | Q(reference__icontains=q)
            )

        # Filter: Payment method
        if method:
            qs = qs.filter(method=method)

        # Filter: Payment type (advance / installment / final / ...)
        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        context["q"] = request.GET.get("q", "")
        context["filter_method"] = request.GET.get("method", "")
        context["filter_payment_type"] = request.GET.get("payment_type", "")

        context["method_choices"] = PaymentMethod.choices
        context["payment_type_choices"] = PaymentType.choices
        return context


class PaymentDetailView(AdminManagerMixin, DetailView):
    model = Payment
    template_name = "sales/payment_detail.html"
    context_object_name = "payment"


class PaymentCreateView(AdminManagerMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form.html"
    success_url = reverse_lazy("sales:payment_list")

    def get_initial(self):
        initial = super().get_initial()
        # Pre-select invoice if ?invoice=<id> in URL
        invoice_id = self.request.GET.get("invoice")
        if invoice_id:
            initial["invoice"] = invoice_id
        return initial

    def form_valid(self, form):
        # who created/owns this payment record
        form.instance.owner = self.request.user
        # who actually received the money
        if not form.instance.received_by_id:
            form.instance.received_by = self.request.user
        return super().form_valid(form)


class PaymentUpdateView(AdminManagerMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form.html"
    success_url = reverse_lazy("sales:payment_list")

# =============================================================================
# Send Email Actions (Proposal / Contract / Invoice / Payment)
# Admin + Manager only
# =============================================================================


def _resolve_client_email(client) -> str:
    """
    Prefer client.email, else fallback to client's primary contact email (if exists).
    """
    if not client:
        return ""

    email = (getattr(client, "email", "") or "").strip()
    if email:
        return email

    primary = getattr(client, "primary_contact", None)
    if primary:
        primary_email = (getattr(primary, "email", "") or "").strip()
        if primary_email:
            return primary_email

    return ""


def _flash_send_result(request, label, to_email, result, extra_tags=""):
    if getattr(result, "ok", False):
        messages.success(
            request,
            f"{label} email sent to {to_email}.",
            extra_tags=extra_tags,
        )
    else:
        error_msg = getattr(result, "error", None) or "Email send failed."
        messages.error(
            request,
            f"{label} email failed: {error_msg}",
            extra_tags=extra_tags,
        )



@method_decorator(require_POST, name="dispatch")
class ProposalSendEmailView(AdminManagerMixin, View):
    """
    Send proposal email immediately using default PROPOSAL template.
    """
    def post(self, request, pk: int):
        proposal = get_object_or_404(
            Proposal.objects.select_related("deal", "deal__client"),
            pk=pk,
        )

        deal = proposal.deal
        client = deal.client if deal else None
        to_email = _resolve_client_email(client)

        if not to_email:
            messages.error(
                request,
                "Client email not found. Please add client email (or primary contact email).",
                extra_tags="scope:proposal scope:email",
            )
            return redirect("sales:proposal_detail", pk=proposal.pk)

        result = send_templated_email(
            template_type=EmailTemplate.TemplateType.PROPOSAL,
            to_emails=to_email,
            context={
                "proposal": proposal,
                "deal": deal,
                "client": client,
            },
        )

        _flash_send_result(
            request,
            label="Proposal",
            to_email=to_email,
            result=result,
            extra_tags="scope:proposal scope:email",
        )
        return redirect("sales:proposal_detail", pk=proposal.pk)


@method_decorator(require_POST, name="dispatch")
class ContractSendEmailView(AdminManagerMixin, View):
    """
    Send contract email immediately using default CONTRACT template.
    """
    def post(self, request, pk: int):
        contract = get_object_or_404(
            Contract.objects.select_related("deal", "deal__client", "proposal"),
            pk=pk,
        )

        deal = contract.deal
        client = deal.client if deal else None
        to_email = _resolve_client_email(client)

        if not to_email:
            messages.error(
                request,
                "Client email not found. Please add client email (or primary contact email).",
                extra_tags="scope:contract scope:email",
            )
            return redirect("sales:contract_detail", pk=contract.pk)

        result = send_templated_email(
            template_type=EmailTemplate.TemplateType.CONTRACT,
            to_emails=to_email,
            context={
                "contract": contract,
                "proposal": contract.proposal,
                "deal": deal,
                "client": client,
            },
        )

        _flash_send_result(
            request,
            label="Contract",
            to_email=to_email,
            result=result,
            extra_tags="scope:contract scope:email",
        )
        return redirect("sales:contract_detail", pk=contract.pk)


@method_decorator(require_POST, name="dispatch")
class InvoiceSendEmailView(AdminManagerMixin, View):
    """
    Send invoice email immediately using default INVOICE template.
    """
    def post(self, request, pk: int):
        invoice = get_object_or_404(
            Invoice.objects.select_related("deal", "deal__client", "contract"),
            pk=pk,
        )

        deal = invoice.deal
        client = deal.client if deal else None
        to_email = _resolve_client_email(client)

        if not to_email:
            messages.error(
                request,
                "Client email not found. Please add client email (or primary contact email).",
                extra_tags="scope:invoice scope:email",
            )
            return redirect("sales:invoice_detail", pk=invoice.pk)

        result = send_templated_email(
            template_type=EmailTemplate.TemplateType.INVOICE,
            to_emails=to_email,
            context={
                "invoice": invoice,
                "deal": deal,
                "client": client,
                "contract": getattr(invoice, "contract", None),
            },
        )

        _flash_send_result(
            request,
            label="Invoice",
            to_email=to_email,
            result=result,
            extra_tags="scope:invoice scope:email",
        )
        return redirect("sales:invoice_detail", pk=invoice.pk)


@method_decorator(require_POST, name="dispatch")
class PaymentSendEmailView(AdminManagerMixin, View):
    """
    Send payment receipt email immediately using default PAYMENT template.
    """
    def post(self, request, pk: int):
        payment = get_object_or_404(
            Payment.objects.select_related("invoice", "invoice__deal", "invoice__deal__client"),
            pk=pk,
        )

        invoice = payment.invoice
        deal = invoice.deal if invoice else None
        client = deal.client if deal else None
        to_email = _resolve_client_email(client)

        if not to_email:
            messages.error(
                request,
                "Client email not found. Please add client email (or primary contact email).",
                extra_tags="scope:payment scope:email",
            )
            return redirect("sales:payment_detail", pk=payment.pk)

        result = send_templated_email(
            template_type=EmailTemplate.TemplateType.PAYMENT,
            to_emails=to_email,
            context={
                "payment": payment,
                "invoice": invoice,
                "deal": deal,
                "client": client,
            },
        )

        _flash_send_result(
            request,
            label="Payment",
            to_email=to_email,
            result=result,
            extra_tags="scope:payment scope:email",
        )
        return redirect("sales:payment_detail", pk=payment.pk)
