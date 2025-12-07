# messaging/views.py
from django.db.models import Q
from django.utils import timezone
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
)

from common.mixins import AdminManagerMixin
from .models import MessageTemplate, Campaign, CampaignRecipient, CampaignStatus,TemplateUsage, Channel,EmailIntegration
from .forms import MessageTemplateForm, CampaignForm, EmailIntegrationForm
from .services import send_campaign
from crm.models import Contact
from events.models import EventPerson
# --------------------------
# Message Templates
# --------------------------

class MessageTemplateListView(AdminManagerMixin, ListView):
    model = MessageTemplate
    template_name = "messaging/template_list.html"
    context_object_name = "templates"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        q = (self.request.GET.get("q") or "").strip()
        usage = (self.request.GET.get("usage") or "").strip()
        channel = (self.request.GET.get("channel") or "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(code__icontains=q)
                | Q(subject__icontains=q)
                | Q(description__icontains=q)
            )

        if usage:
            qs = qs.filter(usage=usage)

        if channel:
            qs = qs.filter(channel=channel)

        return qs
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["template_usage_choices"] = TemplateUsage.choices
        ctx["channel_choices"] = Channel.choices
        return ctx

class MessageTemplateDetailView(AdminManagerMixin, DetailView):
    model = MessageTemplate
    template_name = "messaging/template_detail.html"
    context_object_name = "template_obj"  # avoid clash with 'template' keyword


class MessageTemplateCreateView(AdminManagerMixin, CreateView):
    model = MessageTemplate
    form_class = MessageTemplateForm
    template_name = "messaging/template_form.html"

    def form_valid(self, form):
        if not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("messaging:template_detail", kwargs={"pk": self.object.pk})


class MessageTemplateUpdateView(AdminManagerMixin, UpdateView):
    model = MessageTemplate
    form_class = MessageTemplateForm
    template_name = "messaging/template_form.html"

    def form_valid(self, form):
        if not form.instance.created_by_id:
            form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("messaging:template_detail", kwargs={"pk": self.object.pk})


# --------------------------
# Campaigns
# --------------------------

class CampaignListView(AdminManagerMixin, ListView):
    model = Campaign
    template_name = "messaging/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("template", "integration", "created_by")
        )

        q = (self.request.GET.get("q") or "").strip()
        status = (self.request.GET.get("status") or "").strip()
        date_from = (self.request.GET.get("date_from") or "").strip()
        date_to = (self.request.GET.get("date_to") or "").strip()

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(template__name__icontains=q)
                | Q(template__code__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_choices"] = CampaignStatus.choices
        return ctx


class CampaignDetailView(AdminManagerMixin, DetailView):
    model = Campaign
    template_name = "messaging/campaign_detail.html"
    context_object_name = "campaign"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        campaign = self.object
        ctx["recipients"] = campaign.recipients.all().order_by("email")
        return ctx


class CampaignCreateView(AdminManagerMixin, CreateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "messaging/campaign_form.html"

    def form_valid(self, form):
        campaign = form.save(commit=False)
        campaign.created_by = self.request.user
        campaign.save()

        # --- Build recipients here ---
        # 1) Contacts who allow marketing + have email
        contacts = (
            Contact.objects
            .filter(allow_marketing=True)
            .exclude(email="")
            .select_related("client")
        )

        contact_recipients = [
            CampaignRecipient(
                campaign=campaign,
                client=contact.client,
                contact=contact,
                email=contact.email,
            )
            for contact in contacts
        ]

        # 2) (Optional) EventPersons who allow marketing + have email
        #    Use only if this campaign is for offers to ex-event people, not all campaigns.
        #    For now, you can decide by template.usage == "anniversary" or "generic".
        # Example:
        # if campaign.template.usage in ["generic", "anniversary"]:
        #     people = EventPerson.objects.filter(
        #         allow_marketing=True
        #     ).exclude(email="")
        #     event_recipients = [
        #         CampaignRecipient(
        #             campaign=campaign,
        #             event_person=person,
        #             email=person.email,
        #         )
        #         for person in people
        #     ]
        # else:
        #     event_recipients = []

        event_recipients = []  # keep empty for now unless you want to include them

        CampaignRecipient.objects.bulk_create(
            contact_recipients + event_recipients
        )

        messages.success(
            self.request,
            f"Campaign '{campaign.name}' created with "
            f"{len(contact_recipients) + len(event_recipients)} recipients."
        )
        self.object = campaign
        return redirect("messaging:campaign_detail", pk=campaign.pk)



class CampaignUpdateView(AdminManagerMixin, UpdateView):
    model = Campaign
    form_class = CampaignForm
    template_name = "messaging/campaign_form.html"

    def form_valid(self, form):
        campaign = form.save()
        messages.success(self.request, "Campaign updated.")
        self.object = campaign
        return redirect("messaging:campaign_detail", pk=campaign.pk)


# --------------------------
# Extra: "Send now" action
# --------------------------

@login_required
def campaign_send_now(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    sent = send_campaign(campaign)
    messages.info(request, f"Sent {sent} emails for campaign '{campaign.name}'.")
    return redirect("messaging:campaign_detail", pk=pk)


@method_decorator(login_required, name="dispatch")
class EmailIntegrationSettingsView(AdminManagerMixin, UpdateView):
    """
    Single settings page for email integration.
    Always edits a single EmailIntegration instance.
    """
    model = EmailIntegration
    form_class = EmailIntegrationForm
    template_name = "messaging/integration_settings.html"

    def get_object(self, queryset=None):
        # Try default → first → create new
        obj = EmailIntegration.get_default() or EmailIntegration.objects.first()
        if obj is None:
            obj = EmailIntegration.objects.create(
                name="Default SMTP",
                is_default=True,
            )
        return obj

    def form_valid(self, form):
        obj = form.save()

        # Ensure only one default
        if obj.is_default:
            EmailIntegration.objects.exclude(pk=obj.pk).update(is_default=False)

        messages.success(self.request, "Email integration settings saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("messaging:integration_settings")
