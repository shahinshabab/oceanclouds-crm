# sales/views.py

import json
from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)

from common.mixins import AdminManagerMixin
from crm.models import Client, Contact, Lead
from messaging.models import EmailTemplate
from messaging.utils import send_templated_email
from services.models import Service, Package

from .forms import (
    DealForm,
    ProposalForm,
    ProposalItemFormSet,
    ContractForm,
    InvoiceForm,
    PaymentForm,
    get_catalog_choices,
)
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
try:
    from weasyprint import HTML
except ImportError:
    HTML = None


# ============================================================
# Shared helpers
# ============================================================


def _lead_status(name, fallback):
    return getattr(Lead, name, fallback)


def _set_lead_status(lead, status_attr, fallback):
    if not lead:
        return
    lead.status = _lead_status(status_attr, fallback)
    lead.save(update_fields=["status", "updated_at"])


def _link_client_and_status_to_lead(lead, client, status_attr="STATUS_CONVERTED_TO_CLIENT", fallback="converted_to_client"):
    if not lead:
        return
    lead.client = client
    lead.status = _lead_status(status_attr, fallback)
    lead.save(update_fields=["client", "status", "updated_at"])

class OwnerAssignMixin:
    """
    Automatically assigns owner for models using common.models.Owned.
    """

    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        return super().form_valid(form)


def _copy_lead_data_to_client_if_empty(client, lead):
    """
    Keeps the client clean, but fills missing basic details from the lead.
    """

    changed_fields = []

    if lead.name and not client.name:
        client.name = lead.name
        changed_fields.append("name")

    if lead.name and not client.display_name:
        client.display_name = lead.name
        changed_fields.append("display_name")

    if lead.email and not client.email:
        client.email = lead.email
        changed_fields.append("email")

    if lead.phone and not client.phone:
        client.phone = lead.phone
        changed_fields.append("phone")

    if lead.wedding_city and not client.city:
        client.city = lead.wedding_city
        changed_fields.append("city")

    if lead.wedding_district and not client.district:
        client.district = lead.wedding_district
        changed_fields.append("district")

    if lead.wedding_state and not client.state:
        client.state = lead.wedding_state
        changed_fields.append("state")

    if lead.wedding_country and not client.country:
        client.country = lead.wedding_country
        changed_fields.append("country")

    if changed_fields:
        changed_fields.append("updated_at")
        client.save(update_fields=changed_fields)

    return client


def _get_or_create_client_from_lead(lead, user):
    """
    Your current Deal model requires a client.
    So when a lead becomes a deal, we create/reuse a client.
    """

    if lead.client_id:
        client = lead.client
        _copy_lead_data_to_client_if_empty(client, lead)
        return client

    client = None

    if lead.email:
        client = Client.objects.filter(email__iexact=lead.email).first()

    if client is None and lead.phone:
        client = Client.objects.filter(phone__iexact=lead.phone).first()

    if client is None:
        client = Client.objects.create(
            owner=user,
            name=lead.name,
            display_name=lead.name,
            email=lead.email,
            phone=lead.phone,
            city=lead.wedding_city,
            district=lead.wedding_district,
            state=lead.wedding_state or "Kerala",
            country=lead.wedding_country or "India",
            notes=f"Created from lead #{lead.pk}",
        )
    else:
        _copy_lead_data_to_client_if_empty(client, lead)

    lead.client = client
    lead.save(update_fields=["client", "updated_at"])

    if lead.email or lead.phone or lead.whatsapp:
        existing_contact = client.contacts.filter(
            Q(email__iexact=lead.email) | Q(phone__iexact=lead.phone) | Q(whatsapp__iexact=lead.whatsapp)
        ).first()

        if not existing_contact:
            Contact.objects.create(
                owner=user,
                client=client,
                first_name=lead.name or "Primary Contact",
                email=lead.email,
                phone=lead.phone,
                whatsapp=lead.whatsapp,
                is_primary=not client.contacts.filter(is_primary=True).exists(),
            )

    return client


def _proposal_has_contract(proposal):
    return proposal.contracts.exists()


def _contract_has_invoice(contract):
    return contract.invoices.exists()


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


# ============================================================
# Deals
# ============================================================

class DealListView(AdminManagerMixin, ListView):
    model = Deal
    template_name = "sales/deal_list.html"
    context_object_name = "deals"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "lead", "owner")

        q = (self.request.GET.get("q") or "").strip()
        stage = (self.request.GET.get("stage") or "").strip()
        is_active = (self.request.GET.get("is_active") or "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
                | Q(lead__name__icontains=q)
                | Q(description__icontains=q)
            )

        if stage:
            qs = qs.filter(stage=stage)

        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["filter_stage"] = self.request.GET.get("stage", "")
        context["filter_is_active"] = self.request.GET.get("is_active", "")
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

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("client", "lead", "owner")
            .prefetch_related(
                "proposals",
                "proposals__items",
                "contracts",
                "contracts__items",
                "invoices",
                "invoices__payments",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["proposals"] = self.object.proposals.all().order_by("-created_at")
        context["contracts"] = self.object.contracts.all().order_by("-created_at")
        context["invoices"] = self.object.invoices.all().order_by("-issue_date", "-id")

        return context


class DealCreateView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    model = Deal
    form_class = DealForm
    template_name = "sales/deal_form.html"

    def get_initial(self):
        initial = super().get_initial()

        client_id = self.request.GET.get("client")
        lead_id = self.request.GET.get("lead")

        if client_id:
            initial["client"] = client_id

        if lead_id:
            lead = Lead.objects.filter(pk=lead_id).first()

            if lead:
                initial.update(
                    {
                        "lead": lead.pk,
                        # Important:
                        # Do not create or assign client here.
                        # Client will be created only after proposal acceptance.
                        "name": f"{lead.name} Wedding Deal",
                        "amount": lead.budget_max or lead.budget_min,
                        "expected_close_date": lead.wedding_date,
                        "description": lead.notes,
                        "stage": DealStage.NEW,
                    }
                )

        return initial

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        if self.object.lead_id:
            lead = self.object.lead

            lead.status = _lead_status("STATUS_CONVERTED_TO_DEAL", "converted_to_deal")
            lead.save(update_fields=["status", "updated_at"])

        messages.success(self.request, "Deal created successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:deal_detail", kwargs={"pk": self.object.pk})


class DealUpdateView(AdminManagerMixin, OwnerAssignMixin, UpdateView):
    model = Deal
    form_class = DealForm
    template_name = "sales/deal_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "lead", "owner")

    def get_success_url(self):
        return reverse_lazy("sales:deal_detail", kwargs={"pk": self.object.pk})
    
class DealDeleteView(AdminManagerMixin, DeleteView):
    model = Deal
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("sales:deal_list")

    def get_queryset(self):
        return super().get_queryset().select_related("client", "lead", "owner")


class LeadConvertToDealView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    """
    Flow:
    Lead detail page -> Convert to Deal.

    Important:
    This does NOT create a client.
    Client will be created only after proposal is accepted
    and the user clicks the Create Client button.
    """

    model = Deal
    form_class = DealForm
    template_name = "sales/deal_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.lead = get_object_or_404(
            Lead.objects.select_related("client", "owner", "inquiry"),
            pk=self.kwargs["pk"],
        )

        existing_deal = self.lead.deals.order_by("-created_at").first()
        if existing_deal:
            messages.info(request, "This lead already has a deal.")
            return redirect("sales:deal_detail", pk=existing_deal.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        amount = self.lead.budget_max or self.lead.budget_min

        initial.update(
            {
                "lead": self.lead.pk,
                # Important:
                # Do not assign client here.
                "name": f"{self.lead.name} Wedding Deal",
                "amount": amount,
                "expected_close_date": self.lead.wedding_date,
                "description": self.lead.notes,
                "stage": DealStage.NEW,
                "is_active": True,
            }
        )

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["source_lead"] = self.lead
        context["is_lead_conversion"] = True

        return context

    @transaction.atomic
    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        response = super().form_valid(form)

        self.lead.status = _lead_status("STATUS_CONVERTED_TO_DEAL", "converted_to_deal")
        self.lead.save(update_fields=["status", "updated_at"])

        messages.success(self.request, "Lead converted to deal successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:deal_detail", kwargs={"pk": self.object.pk})

# ============================================================
# Proposals
# ============================================================

class ProposalListView(AdminManagerMixin, ListView):
    model = Proposal
    template_name = "sales/proposal_list.html"
    context_object_name = "proposals"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("deal", "deal__client", "owner")

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        deal_stage = (self.request.GET.get("deal_stage") or "").strip()

        if q:
            qs = qs.filter(
                Q(deal__name__icontains=q)
                | Q(deal__client__name__icontains=q)
                | Q(title__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        if deal_stage:
            qs = qs.filter(deal__stage=deal_stage)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["filter_status"] = self.request.GET.get("status", "")
        context["filter_deal_stage"] = self.request.GET.get("deal_stage", "")
        context["status_choices"] = ProposalStatus.choices
        context["deal_stage_choices"] = DealStage.choices

        return context


class ProposalDetailView(AdminManagerMixin, DetailView):
    model = Proposal
    template_name = "sales/proposal_detail.html"
    context_object_name = "proposal"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "deal__lead", "owner")
            .prefetch_related("items", "contracts")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_contract"] = self.object.contracts.exists()
        context["contract"] = self.object.contracts.order_by("-created_at").first()
        return context


class ProposalCreateView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "sales/proposal_form.html"

    def get_initial(self):
        initial = super().get_initial()

        deal_id = self.request.GET.get("deal")
        if deal_id:
            deal = Deal.objects.filter(pk=deal_id).select_related("client").first()

            if deal:
                next_version = deal.proposals.count() + 1

                initial.update(
                    {
                        "deal": deal.pk,
                        "title": f"Proposal for {deal.name}",
                        "version": next_version,
                        "status": ProposalStatus.DRAFT,
                    }
                )

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
            context["item_formset"] = ProposalItemFormSet(catalog_choices=catalog_choices)

        return context

    @transaction.atomic
    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        context = self.get_context_data(form=form)
        item_formset = context["item_formset"]

        if not item_formset.is_valid():
            return self.render_to_response(context)

        self.object = form.save()

        item_formset.instance = self.object
        item_formset.save()

        self.object.recalculate_totals(save=True)

        deal = self.object.deal
        deal.stage = DealStage.PROPOSAL_SENT
        deal.save(update_fields=["stage", "updated_at"])

        if deal.lead_id:
            lead = deal.lead
            _set_lead_status(lead, "STATUS_PROPOSAL_SENT", "proposal_sent")

        messages.success(self.request, "Proposal created successfully.")

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("sales:proposal_detail", kwargs={"pk": self.object.pk})


class ProposalUpdateView(AdminManagerMixin, OwnerAssignMixin, UpdateView):
    model = Proposal
    form_class = ProposalForm
    template_name = "sales/proposal_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("deal", "deal__client", "owner")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        services_price_map, packages_price_map = _get_price_maps()
        context["services_price_map_json"] = mark_safe(json.dumps(services_price_map))
        context["packages_price_map_json"] = mark_safe(json.dumps(packages_price_map))

        catalog_choices = get_catalog_choices()

        if self.request.method == "POST":
            context["item_formset"] = ProposalItemFormSet(
                self.request.POST,
                instance=self.object,
                catalog_choices=catalog_choices,
            )
        else:
            context["item_formset"] = ProposalItemFormSet(
                instance=self.object,
                catalog_choices=catalog_choices,
            )

        return context

    @transaction.atomic
    def form_valid(self, form):
        context = self.get_context_data(form=form)
        item_formset = context["item_formset"]

        if not item_formset.is_valid():
            return self.render_to_response(context)

        self.object = form.save()

        item_formset.instance = self.object
        item_formset.save()

        self.object.recalculate_totals(save=True)

        messages.success(self.request, "Proposal updated successfully.")

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("sales:proposal_detail", kwargs={"pk": self.object.pk})

class ProposalDeleteView(AdminManagerMixin, DeleteView):
    model = Proposal
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("sales:proposal_list")

    def get_queryset(self):
        return super().get_queryset().select_related("deal", "deal__client", "owner")

@method_decorator(require_POST, name="dispatch")
class ProposalAcceptView(AdminManagerMixin, View):
    """
    Proposal accepted:
    - Proposal status = accepted
    - Deal stage = won
    - Lead status = proposal accepted / converted pending client creation
    - Does NOT create client automatically
    """

    @transaction.atomic
    def post(self, request, pk):
        proposal = get_object_or_404(
            Proposal.objects.select_related("deal", "deal__client", "deal__lead"),
            pk=pk,
        )

        deal = proposal.deal
        lead = deal.lead

        proposal.status = ProposalStatus.ACCEPTED
        proposal.save(update_fields=["status", "updated_at"])

        deal.stage = DealStage.WON
        deal.closed_on = timezone.localdate()
        deal.is_active = True
        deal.save(update_fields=["stage", "closed_on", "is_active", "updated_at"])

        if lead:
            # Do not assign client here.
            # Client will be created using Create Client button.
            _set_lead_status(lead, "STATUS_PROPOSAL_ACCEPTED", "proposal_accepted")

        messages.success(
            request,
            "Proposal accepted. You can now create the client using the Create Client button.",
        )

        return redirect("sales:proposal_detail", pk=proposal.pk)

class ProposalConvertToContractView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    """
    Proposal detail page -> Convert to Contract.

    Contract can be created only after:
    1. Proposal is accepted
    2. Client is created/linked to the deal
    """

    model = Contract
    form_class = ContractForm
    template_name = "sales/contract_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.proposal = get_object_or_404(
            Proposal.objects.select_related(
                "deal",
                "deal__client",
                "deal__lead",
            ),
            pk=self.kwargs["pk"],
        )

        deal = self.proposal.deal

        # 1. Proposal must be accepted first
        if self.proposal.status != ProposalStatus.ACCEPTED:
            messages.error(
                request,
                "Please accept the proposal before creating a contract.",
            )
            return redirect("sales:proposal_detail", pk=self.proposal.pk)

        # 2. Client must be created/linked before contract
        if not deal.client_id:
            messages.error(
                request,
                "Please create the client from the accepted proposal before creating a contract.",
            )
            return redirect("sales:proposal_detail", pk=self.proposal.pk)

        # 3. Prevent duplicate contract
        existing_contract = self.proposal.contracts.order_by("-created_at").first()
        if existing_contract:
            messages.info(request, "This proposal already has a contract.")
            return redirect("sales:contract_detail", pk=existing_contract.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        initial.update(
            {
                "deal": self.proposal.deal_id,
                "proposal": self.proposal.pk,
                "status": ContractStatus.DRAFT,
                "start_date": timezone.localdate(),
                "terms": self.proposal.notes,
            }
        )

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["source_proposal"] = self.proposal
        context["is_proposal_conversion"] = True

        return context

    @transaction.atomic
    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        response = super().form_valid(form)

        self.object.populate_from_proposal(
            self.proposal,
            clear_existing=True,
        )

        deal = self.proposal.deal

        deal.stage = DealStage.WON
        deal.closed_on = timezone.localdate()
        deal.save(update_fields=["stage", "closed_on", "updated_at"])

        if deal.lead_id:
            lead = deal.lead
            _link_client_and_status_to_lead(lead, deal.client)

        messages.success(
            self.request,
            "Contract created from proposal successfully.",
        )

        return response

    def get_success_url(self):
        return reverse_lazy(
            "sales:contract_detail",
            kwargs={"pk": self.object.pk},
        )
    
@method_decorator(require_POST, name="dispatch")
class ProposalCreateClientView(AdminManagerMixin, View):
    """
    Creates/links a client from proposal flow.

    Correct flow:
    Deal is created without client.
    Proposal is generated.
    Proposal is accepted.
    Then user clicks Create Client.
    Only here the client is created or linked.
    """

    @transaction.atomic
    def post(self, request, pk):
        proposal = get_object_or_404(
            Proposal.objects.select_related(
                "deal",
                "deal__client",
                "deal__lead",
            ),
            pk=pk,
        )

        deal = proposal.deal
        lead = deal.lead

        if proposal.status != ProposalStatus.ACCEPTED:
            messages.error(
                request,
                "Please accept the proposal before creating a client.",
                extra_tags="scope:proposal scope:client",
            )
            return redirect("sales:proposal_detail", pk=proposal.pk)

        # If client already exists, do not duplicate.
        if deal.client_id:
            client = deal.client

            proposal.status = ProposalStatus.ACCEPTED
            proposal.save(update_fields=["status", "updated_at"])

            deal.stage = DealStage.WON
            deal.closed_on = timezone.localdate()
            deal.save(update_fields=["stage", "closed_on", "updated_at"])

            if lead:
                _link_client_and_status_to_lead(lead, client)

            messages.info(
                request,
                "Client already exists. Proposal marked as accepted.",
                extra_tags="scope:proposal scope:client",
            )

            return redirect("crm:client_detail", pk=client.pk)

        client = None

        # Try to reuse existing client using lead email/phone.
        if lead and lead.email:
            client = Client.objects.filter(email__iexact=lead.email).first()

        if client is None and lead and lead.phone:
            client = Client.objects.filter(phone__iexact=lead.phone).first()

        # Create client only here.
        if client is None:
            if lead:
                client = Client.objects.create(
                    owner=request.user,
                    name=lead.name or deal.name,
                    display_name=lead.name or deal.name,
                    email=lead.email or "",
                    phone=lead.phone or "",
                    city=lead.wedding_city or "",
                    district=lead.wedding_district or "",
                    state=lead.wedding_state or "Kerala",
                    country=lead.wedding_country or "India",
                    is_active=True,
                    notes=f"Created from accepted proposal: {proposal.title}",
                )
            else:
                client = Client.objects.create(
                    owner=request.user,
                    name=deal.name,
                    display_name=deal.name,
                    is_active=True,
                    notes=f"Created from accepted proposal: {proposal.title}",
                )
        else:
            if lead:
                _copy_lead_data_to_client_if_empty(client, lead)

        # Link client to deal.
        deal.client = client
        deal.stage = DealStage.WON
        deal.closed_on = timezone.localdate()
        deal.is_active = True
        deal.save(update_fields=["client", "stage", "closed_on", "is_active", "updated_at"])

        # Link client to lead.
        if lead:
            _link_client_and_status_to_lead(lead, client)

            if lead.email or lead.phone or lead.whatsapp:
                existing_contact = client.contacts.filter(
                    Q(email__iexact=lead.email)
                    | Q(phone__iexact=lead.phone)
                    | Q(whatsapp__iexact=lead.whatsapp)
                ).first()

                if not existing_contact:
                    Contact.objects.create(
                        owner=request.user,
                        client=client,
                        first_name=lead.name or "Primary Contact",
                        email=lead.email or "",
                        phone=lead.phone or "",
                        whatsapp=lead.whatsapp or "",
                        is_primary=not client.contacts.filter(is_primary=True).exists(),
                    )

        proposal.status = ProposalStatus.ACCEPTED
        proposal.save(update_fields=["status", "updated_at"])

        messages.success(
            request,
            "Client created successfully from accepted proposal.",
            extra_tags="scope:proposal scope:client",
        )

        return redirect("crm:client_detail", pk=client.pk)


# ============================================================
# Contracts
# ============================================================

class ContractListView(AdminManagerMixin, ListView):
    model = Contract
    template_name = "sales/contract_list.html"
    context_object_name = "contracts"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("deal", "proposal", "deal__client", "owner")
            .prefetch_related("invoices")
        )

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        deal_stage = (self.request.GET.get("deal_stage") or "").strip()

        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(deal__name__icontains=q)
                | Q(deal__client__name__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        if deal_stage:
            qs = qs.filter(deal__stage=deal_stage)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["filter_status"] = self.request.GET.get("status", "")
        context["filter_deal_stage"] = self.request.GET.get("deal_stage", "")
        context["status_choices"] = ContractStatus.choices
        context["deal_stage_choices"] = DealStage.choices

        return context


class ContractDetailView(AdminManagerMixin, DetailView):
    model = Contract
    template_name = "sales/contract_detail.html"
    context_object_name = "contract"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "proposal", "owner")
            .prefetch_related("items", "invoices")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["has_invoice"] = _contract_has_invoice(self.object)
        context["invoice"] = self.object.invoices.order_by("-issue_date", "-created_at").first()

        return context


class ContractCreateView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    model = Contract
    form_class = ContractForm
    template_name = "sales/contract_form.html"

    def get_initial(self):
        initial = super().get_initial()

        deal_id = self.request.GET.get("deal")
        proposal_id = self.request.GET.get("proposal")

        if deal_id:
            initial["deal"] = deal_id

        if proposal_id:
            proposal = Proposal.objects.filter(pk=proposal_id).select_related("deal").first()

            if proposal:
                initial.update(
                    {
                        "deal": proposal.deal_id,
                        "proposal": proposal.pk,
                        "terms": proposal.notes,
                    }
                )

        return initial

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        contract = self.object

        if contract.proposal_id and not contract.items.exists():
            contract.populate_from_proposal(contract.proposal, clear_existing=True)

        messages.success(self.request, "Contract created successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:contract_detail", kwargs={"pk": self.object.pk})


class ContractUpdateView(AdminManagerMixin, OwnerAssignMixin, UpdateView):
    model = Contract
    form_class = ContractForm
    template_name = "sales/contract_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("deal", "proposal", "owner")

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        contract = self.object

        if contract.proposal_id and not contract.items.exists():
            contract.populate_from_proposal(contract.proposal, clear_existing=True)

        messages.success(self.request, "Contract updated successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:contract_detail", kwargs={"pk": self.object.pk})

class ContractDeleteView(AdminManagerMixin, DeleteView):
    model = Contract
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("sales:contract_list")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "proposal", "owner")
        )
    

class ContractGenerateInvoiceView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    """
    Contract detail page -> Generate Invoice.
    Creates invoice and copies contract items into invoice items.
    """

    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.contract = get_object_or_404(
            Contract.objects.select_related("deal", "deal__client", "proposal"),
            pk=self.kwargs["pk"],
        )

        existing_invoice = self.contract.invoices.order_by("-issue_date", "-created_at").first()
        if existing_invoice:
            messages.info(request, "This contract already has an invoice.")
            return redirect("sales:invoice_detail", pk=existing_invoice.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        today = timezone.localdate()

        initial.update(
            {
                "deal": self.contract.deal_id,
                "contract": self.contract.pk,
                "issue_date": today,
                "due_date": today + timedelta(days=7),
                "status": InvoiceStatus.DRAFT,
                "notes": f"Invoice generated from contract {self.contract.number}",
            }
        )

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["source_contract"] = self.contract
        context["is_contract_conversion"] = True

        return context

    @transaction.atomic
    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        response = super().form_valid(form)

        self.object.populate_from_contract(self.contract, clear_existing=True)

        messages.success(self.request, "Invoice generated from contract successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:invoice_detail", kwargs={"pk": self.object.pk})


# ============================================================
# Invoices
# ============================================================

class InvoiceListView(AdminManagerMixin, ListView):
    model = Invoice
    template_name = "sales/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def _get_period_dates(self, period_key):
        """
        Returns (start_date, end_date) for invoice issue_date filtering.
        """
        today = timezone.localdate()

        if period_key == "this_month":
            start = today.replace(day=1)
            end = today
            return start, end

        if period_key == "last_month":
            first_this_month = today.replace(day=1)
            last_previous_month = first_this_month - timedelta(days=1)
            start = last_previous_month.replace(day=1)
            end = last_previous_month
            return start, end

        if period_key == "last_3_months":
            first_this_month = today.replace(day=1)
            approx_two_months_back = first_this_month - timedelta(days=62)
            start = approx_two_months_back.replace(day=1)
            end = today
            return start, end

        if period_key == "last_year":
            start = date(today.year - 1, 1, 1)
            end = date(today.year - 1, 12, 31)
            return start, end

        return None, None

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "contract", "owner")
            .prefetch_related("payments")
        )

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        period = (self.request.GET.get("period") or "").strip()

        if q:
            qs = qs.filter(
                Q(number__icontains=q)
                | Q(deal__client__name__icontains=q)
                | Q(deal__client__display_name__icontains=q)
                | Q(deal__client__email__icontains=q)
                | Q(deal__client__phone__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        start_date, end_date = self._get_period_dates(period)
        if start_date and end_date:
            qs = qs.filter(issue_date__gte=start_date, issue_date__lte=end_date)

        return qs.order_by("-issue_date", "-id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["filter_status"] = self.request.GET.get("status", "")
        context["filter_period"] = self.request.GET.get("period", "")

        context["status_choices"] = InvoiceStatus.choices
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

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "contract", "owner")
            .prefetch_related(
                "items",
                "items__contract_item",
                "items__contract_item__service",
                "items__contract_item__package",
                "payments",
                "payments__received_by",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pdf_download_url"] = reverse("sales:invoice_download", args=[self.object.pk])
        context["payments"] = self.object.payments.all().order_by("-date", "-created_at")
        context["client"] = self.object.deal.client if self.object.deal_id else None
        return context


class InvoiceCreateView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"

    def get_initial(self):
        initial = super().get_initial()

        deal_id = self.request.GET.get("deal")
        contract_id = self.request.GET.get("contract")
        today = timezone.localdate()

        if deal_id:
            initial["deal"] = deal_id

        if contract_id:
            contract = Contract.objects.filter(pk=contract_id).select_related("deal").first()

            if contract:
                initial.update(
                    {
                        "deal": contract.deal_id,
                        "contract": contract.pk,
                        "issue_date": today,
                        "due_date": today + timedelta(days=7),
                    }
                )
        else:
            initial.setdefault("issue_date", today)
            initial.setdefault("due_date", today + timedelta(days=7))

        return initial

    def _get_contract_for_invoice(self, invoice):
        contract_id = self.request.POST.get("contract") or self.request.GET.get("contract")

        if contract_id:
            return Contract.objects.filter(pk=contract_id, deal=invoice.deal).first()

        return invoice.deal.contracts.order_by("-signed_date", "-created_at").first()

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        contract = self._get_contract_for_invoice(self.object)

        if contract:
            self.object.populate_from_contract(contract, clear_existing=True)

        messages.success(self.request, "Invoice created successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("sales:invoice_detail", kwargs={"pk": self.object.pk})


class InvoiceUpdateView(AdminManagerMixin, OwnerAssignMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "sales/invoice_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("deal", "contract", "owner")

    def get_success_url(self):
        return reverse_lazy("sales:invoice_detail", kwargs={"pk": self.object.pk})

class InvoiceDeleteView(AdminManagerMixin, DeleteView):
    model = Invoice
    template_name = "common/confirm_delete.html"
    success_url = reverse_lazy("sales:invoice_list")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("deal", "deal__client", "contract", "owner")
            .prefetch_related("payments", "items")
        )
    
class InvoicePDFDownloadView(AdminManagerMixin, DetailView):
    model = Invoice

    def get(self, request, *args, **kwargs):
        if HTML is None:
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


# ============================================================
# Payments
# ============================================================

class PaymentListView(AdminManagerMixin, ListView):
    model = Payment
    template_name = "sales/payment_list.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related(
                "invoice",
                "invoice__deal",
                "invoice__deal__client",
                "received_by",
                "owner",
            )
        )

        q = (self.request.GET.get("q") or "").strip()
        method = (self.request.GET.get("method") or "").strip()
        payment_type = (self.request.GET.get("payment_type") or "").strip()

        if q:
            qs = qs.filter(
                Q(invoice__number__icontains=q)
                | Q(invoice__deal__client__name__icontains=q)
                | Q(invoice__deal__client__display_name__icontains=q)
                | Q(reference__icontains=q)
            )

        if method:
            qs = qs.filter(method=method)

        if payment_type:
            qs = qs.filter(payment_type=payment_type)

        return qs


class PaymentDetailView(AdminManagerMixin, DetailView):
    model = Payment
    template_name = "sales/payment_detail.html"
    context_object_name = "payment"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "invoice",
                "invoice__deal",
                "invoice__deal__client",
                "received_by",
                "owner",
            )
        )


class PaymentCreateView(AdminManagerMixin, OwnerAssignMixin, CreateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form.html"

    def get_initial(self):
        initial = super().get_initial()

        invoice_id = self.request.GET.get("invoice")
        if invoice_id:
            invoice = Invoice.objects.filter(pk=invoice_id).first()

            if invoice:
                initial.update(
                    {
                        "invoice": invoice.pk,
                        "date": timezone.localdate(),
                        "amount": invoice.balance,
                    }
                )

        return initial

    @transaction.atomic
    def form_valid(self, form):
        if not form.instance.owner_id:
            form.instance.owner = self.request.user

        if not form.instance.received_by_id:
            form.instance.received_by = self.request.user

        response = super().form_valid(form)

        messages.success(self.request, "Payment added successfully.")

        return response

    def get_success_url(self):
        if self.object.invoice_id:
            return reverse_lazy("sales:invoice_detail", kwargs={"pk": self.object.invoice_id})

        return reverse_lazy("sales:payment_list")


class PaymentUpdateView(AdminManagerMixin, OwnerAssignMixin, UpdateView):
    model = Payment
    form_class = PaymentForm
    template_name = "sales/payment_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("invoice", "received_by", "owner")

    def get_success_url(self):
        if self.object.invoice_id:
            return reverse_lazy("sales:invoice_detail", kwargs={"pk": self.object.invoice_id})

        return reverse_lazy("sales:payment_list")

class PaymentDeleteView(AdminManagerMixin, DeleteView):
    model = Payment
    template_name = "common/confirm_delete.html"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related(
                "invoice",
                "invoice__deal",
                "invoice__deal__client",
                "received_by",
                "owner",
            )
        )

    def get_success_url(self):
        if self.object.invoice_id:
            return reverse_lazy(
                "sales:invoice_detail",
                kwargs={"pk": self.object.invoice_id},
            )

        return reverse_lazy("sales:payment_list")
    
# ============================================================
# Send Email Actions
# ============================================================

def _resolve_client_email(client):
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
    def post(self, request, pk):
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
                "Client email not found. Please add client email or primary contact email.",
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

        if getattr(result, "ok", False):
            proposal.status = ProposalStatus.SENT
            proposal.save(update_fields=["status", "updated_at"])

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
    def post(self, request, pk):
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
                "Client email not found. Please add client email or primary contact email.",
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

        if getattr(result, "ok", False):
            contract.status = ContractStatus.PENDING_SIGNATURE
            contract.save(update_fields=["status", "updated_at"])

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
    def post(self, request, pk):
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
                "Client email not found. Please add client email or primary contact email.",
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
                "contract": invoice.contract,
            },
        )

        if getattr(result, "ok", False):
            if invoice.status == InvoiceStatus.DRAFT:
                invoice.status = InvoiceStatus.ISSUED
                invoice.save(update_fields=["status", "updated_at"])

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
    def post(self, request, pk):
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
                "Client email not found. Please add client email or primary contact email.",
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