# messaging/views.py
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DeleteView,
    DetailView,
)

from common.mixins import AdminManagerMixin  # 🔹 role-based access (admin + manager)

from .forms import EmailTemplateForm, CampaignForm
from .models import EmailTemplate, Campaign, CampaignRecipient


# ---------------------------------------------------------------------------
# Email Template Views
# ---------------------------------------------------------------------------


class EmailTemplateListView(AdminManagerMixin, ListView):
    """
    List of templates.
    Admin + Manager can see all templates (role-based via AdminManagerMixin).
    """
    model = EmailTemplate
    template_name = "messaging/emailtemplate_list.html"
    context_object_name = "templates"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        # Search by name or subject
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(subject__icontains=q))

        # Filter by type
        ttype = self.request.GET.get("type") or ""
        if ttype:
            qs = qs.filter(type=ttype)

        # Filter by active / inactive
        is_active = self.request.GET.get("is_active")
        if is_active == "1":
            qs = qs.filter(is_active=True)
        elif is_active == "0":
            qs = qs.filter(is_active=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # For dynamic dropdown options
        context["type_choices"] = EmailTemplate.TemplateType.choices
        context["current_type"] = self.request.GET.get("type") or ""
        context["current_q"] = self.request.GET.get("q") or ""
        context["current_is_active"] = self.request.GET.get("is_active") or ""
        return context


class EmailTemplateDetailView(AdminManagerMixin, DetailView):
    """
    Detail: admin + manager can view.
    Template can access template.owner / template.created_at from Owned/TimeStamped.
    """
    model = EmailTemplate
    template_name = "messaging/emailtemplate_detail.html"
    context_object_name = "template"


class EmailTemplateCreateView(AdminManagerMixin, CreateView):
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = "messaging/emailtemplate_form.html"

    def form_valid(self, form):
        # Owned mixin: set owner
        if not form.instance.owner_id:
            form.instance.owner = self.request.user
        messages.success(self.request, "Email template created.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("messaging:template_list")


class EmailTemplateUpdateView(AdminManagerMixin, UpdateView):
    model = EmailTemplate
    form_class = EmailTemplateForm
    template_name = "messaging/emailtemplate_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Email template updated.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("messaging:template_detail", args=[self.object.pk])


class EmailTemplateDeleteView(AdminManagerMixin, DeleteView):
    model = EmailTemplate
    success_url = reverse_lazy("messaging:template_list")

    def post(self, request, *args, **kwargs):
        messages.success(request, "Email template deleted.")
        return super().post(request, *args, **kwargs)

class EmailTemplatePreviewView(AdminManagerMixin, DetailView):
    """
    Renders the saved HTML body as a full-page preview.
    """
    model = EmailTemplate
    template_name = "messaging/emailtemplate_preview.html"
    context_object_name = "template"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["back_url"] = reverse("messaging:template_detail", args=[self.object.pk])
        return ctx

# ---------------------------------------------------------------------------
# Campaign Views
# ---------------------------------------------------------------------------


class CampaignListView(AdminManagerMixin, ListView):
    """
    Admin + Manager can see all campaigns.
    """
    model = Campaign
    template_name = "messaging/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("template", "owner")
        )

        # Search by name or description
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(description__icontains=q)
            )

        # Filter by status
        status = self.request.GET.get("status") or ""
        if status:
            qs = qs.filter(status=status)

        # Filter by target type
        target_type = self.request.GET.get("target_type") or ""
        if target_type:
            qs = qs.filter(target_type=target_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Campaign.Status.choices
        context["target_type_choices"] = Campaign.TargetType.choices
        context["current_q"] = self.request.GET.get("q") or ""
        context["current_status"] = self.request.GET.get("status") or ""
        context["current_target_type"] = self.request.GET.get("target_type") or ""
        return context


class CampaignDetailView(AdminManagerMixin, DetailView):
    model = Campaign
    template_name = "messaging/campaign_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        campaign = self.object
        qs = campaign.recipients.all()

        context["sent_count"] = qs.filter(status=CampaignRecipient.SendStatus.SENT).count()
        context["pending_count"] = qs.filter(status=CampaignRecipient.SendStatus.PENDING).count()
        context["failed_count"] = qs.filter(status=CampaignRecipient.SendStatus.FAILED).count()
        context["total_recipients"] = qs.count()

        # only show 10 rows on page
        context["recipients"] = qs.order_by("status", "email")[:10]
        return context



class CampaignDeleteView(AdminManagerMixin, DeleteView):
    model = Campaign
    success_url = reverse_lazy("messaging:campaign_list")

    def post(self, request, *args, **kwargs):
        messages.success(request, "Campaign deleted.")
        return super().post(request, *args, **kwargs)



class CampaignPauseView(AdminManagerMixin, DetailView):
    model = Campaign

    def post(self, request, *args, **kwargs):
        campaign = self.get_object()
        campaign.status = Campaign.Status.PAUSED
        campaign.save(update_fields=["status"])
        messages.info(request, f"Campaign '{campaign.name}' paused.")
        return redirect("messaging:campaign_detail", pk=campaign.pk)


class CampaignResumeView(AdminManagerMixin, DetailView):
    model = Campaign

    def post(self, request, *args, **kwargs):
        campaign = self.get_object()
        # Usually from PAUSED -> SCHEDULED (cron will pick it)
        campaign.status = Campaign.Status.SCHEDULED
        campaign.save(update_fields=["status"])
        messages.success(request, f"Campaign '{campaign.name}' resumed.")
        return redirect("messaging:campaign_detail", pk=campaign.pk)



# messaging/views.py
from django.contrib import messages
from django.db import transaction
from django.urls import reverse
from django.views.generic import CreateView, UpdateView, DetailView, ListView, DeleteView
from django.db.models import Q

from common.mixins import AdminManagerMixin
from .forms import CampaignForm
from .models import Campaign, CampaignRecipient
from .utils import parse_custom_list

from crm.models import Client, Contact  # adjust import path if different


def sync_campaign_recipients(campaign: Campaign):
    """
    Populate CampaignRecipient based on campaign.target_type.

    Safe rule:
    - Keep SENT recipients (don’t delete history)
    - Replace PENDING/FAILED recipients based on the new source
    """
    # delete only non-sent rows (so you keep history)
    campaign.recipients.exclude(status=CampaignRecipient.SendStatus.SENT).delete()

    new_rows = []

    if campaign.target_type == Campaign.TargetType.CUSTOM_LIST:
        parsed = parse_custom_list(campaign.custom_list_raw)

        for item in parsed:
            first_name = (item["name"].split(" ", 1)[0] if item["name"] else "")
            last_name = (item["name"].split(" ", 1)[1] if item["name"] and " " in item["name"] else "")

            new_rows.append(
                CampaignRecipient(
                    campaign=campaign,
                    email=item["email"],
                    first_name=first_name,
                    last_name=last_name,
                    company="",
                    status=CampaignRecipient.SendStatus.PENDING,
                )
            )

    elif campaign.target_type == Campaign.TargetType.CLIENT_MARKETING:
        # Active clients -> contacts allow_marketing -> valid email
        qs = (
            Contact.objects
            .select_related("client")
            .filter(
                client__is_active=True,
                allow_marketing=True,
            )
            .exclude(email="")
        )

        for c in qs:
            new_rows.append(
                CampaignRecipient(
                    campaign=campaign,
                    email=c.email.strip().lower(),
                    first_name=c.first_name or "",
                    last_name=c.last_name or "",
                    company=str(c.client),  # client name
                    status=CampaignRecipient.SendStatus.PENDING,
                )
            )

    # bulk insert (ignore conflicts because unique_together campaign+email)
    # If your DB is Postgres, you can use ignore_conflicts=True.
    if new_rows:
        CampaignRecipient.objects.bulk_create(new_rows, ignore_conflicts=True)


class CampaignCreateView(AdminManagerMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "messaging/campaign_form.html"

    @transaction.atomic
    def form_valid(self, form):
        if not form.instance.owner_id:
            form.instance.owner = self.request.user

        response = super().form_valid(form)

        sync_campaign_recipients(self.object)
        messages.success(self.request, "Campaign created and recipients synced.")
        return response

    def get_success_url(self):
        return reverse("messaging:campaign_list")


class CampaignUpdateView(AdminManagerMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "messaging/campaign_form.html"

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        sync_campaign_recipients(self.object)
        messages.success(self.request, "Campaign updated and recipients synced.")
        return response

    def get_success_url(self):
        return reverse("messaging:campaign_detail", args=[self.object.pk])
