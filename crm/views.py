# crm/views.py

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)

from .models import Client, Contact, Lead, Inquiry, Review
from .forms import (
    ClientForm,
    ContactForm,
    LeadForm,
    InquiryForm,
    ReviewForm,
)

from common.mixins import (
    AdminCRMManagerMixin,
    InquiryManagerMixin,
    StaffAllMixin,
)


# ============================================================
# Shared helpers
# ============================================================

class OwnerAssignMixin:
    """
    Automatically assigns owner for models using common.models.Owned.
    """

    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        return super().form_valid(form)


# ============================================================
# Client Reviews
# Access: Admin + CRM Manager only
# ============================================================

class ReviewListView(AdminCRMManagerMixin, ListView):
    model = Review
    template_name = "crm/review_list.html"
    context_object_name = "reviews"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "owner")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(comment__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
                | Q(next_action__icontains=q)
            )

        client_id = (self.request.GET.get("client") or "").strip()
        if client_id:
            qs = qs.filter(client_id=client_id)

        rating = (self.request.GET.get("rating") or "").strip()
        if rating.isdigit():
            qs = qs.filter(rating=int(rating))

        action_due = (self.request.GET.get("action_due") or "").strip()
        if action_due:
            today = timezone.localdate()

            if action_due == "overdue":
                qs = qs.filter(next_action_date__lt=today)
            elif action_due == "today":
                qs = qs.filter(next_action_date=today)
            elif action_due == "upcoming":
                qs = qs.filter(next_action_date__gt=today)
            elif action_due == "no_date":
                qs = qs.filter(next_action_date__isnull=True)

        return qs


class ReviewDetailView(AdminCRMManagerMixin, DetailView):
    model = Review
    template_name = "crm/review_detail.html"
    context_object_name = "review"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")


class ReviewCreateView(AdminCRMManagerMixin, OwnerAssignMixin, CreateView):
    model = Review
    form_class = ReviewForm
    template_name = "crm/review_form.html"

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")

        if client_id:
            initial["client"] = client_id

        return initial

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:review_list")


class ReviewUpdateView(AdminCRMManagerMixin, OwnerAssignMixin, UpdateView):
    model = Review
    form_class = ReviewForm
    template_name = "crm/review_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:review_list")


class ReviewDeleteView(AdminCRMManagerMixin, DeleteView):
    model = Review
    template_name = "crm/review_delete.html"
    context_object_name = "review"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:review_list")

    def form_valid(self, form):
        review_title = self.object.title or "Review"
        messages.success(self.request, f"Review '{review_title}' deleted successfully.")
        return super().form_valid(form)


# ============================================================
# Contacts
# Access: Admin + CRM Manager only
# ============================================================

class ContactListView(AdminCRMManagerMixin, ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "owner")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(whatsapp__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
            )

        role = (self.request.GET.get("role") or "").strip()
        if role:
            qs = qs.filter(role=role)

        is_primary = (self.request.GET.get("is_primary") or "").strip()
        if is_primary == "1":
            qs = qs.filter(is_primary=True)
        elif is_primary == "0":
            qs = qs.filter(is_primary=False)

        return qs


class ContactDetailView(AdminCRMManagerMixin, DetailView):
    model = Contact
    template_name = "crm/contact_detail.html"
    context_object_name = "contact"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")


class ContactCreateView(AdminCRMManagerMixin, OwnerAssignMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")

        if client_id:
            initial["client"] = client_id

        return initial

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:contact_list")


class ContactUpdateView(AdminCRMManagerMixin, OwnerAssignMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:contact_list")


class ContactDeleteView(AdminCRMManagerMixin, DeleteView):
    model = Contact
    template_name = "crm/contact_delete.html"
    context_object_name = "contact"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "owner")

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:contact_list")

    def form_valid(self, form):
        contact_name = f"{self.object.first_name} {self.object.last_name}".strip()
        messages.success(self.request, f"Contact '{contact_name}' deleted successfully.")
        return super().form_valid(form)


# ============================================================
# Clients
# Access: Admin + CRM Manager only
# ============================================================

class ClientListView(AdminCRMManagerMixin, ListView):
    model = Client
    template_name = "crm/client_list.html"
    context_object_name = "clients"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("owner")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(display_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(city__icontains=q)
                | Q(district__icontains=q)
                | Q(state__icontains=q)
                | Q(country__icontains=q)
            )

        is_active = (self.request.GET.get("is_active") or "").strip()
        if is_active == "1":
            qs = qs.filter(is_active=True)
        elif is_active == "0":
            qs = qs.filter(is_active=False)

        district = (self.request.GET.get("district") or "").strip()
        if district:
            qs = qs.filter(district__icontains=district)

        country = (self.request.GET.get("country") or "").strip()
        if country:
            qs = qs.filter(country__iexact=country)

        return qs


class ClientDetailView(AdminCRMManagerMixin, DetailView):
    model = Client
    template_name = "crm/client_detail.html"
    context_object_name = "client"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("owner")
            .prefetch_related(
                "contacts",
                "leads",
                "reviews",
                "inquiries",
                "deals",
                "deals__proposals",
                "deals__contracts",
                "deals__invoices",
            )
        )

class ClientCreateView(AdminCRMManagerMixin, OwnerAssignMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "crm/client_form.html"

    def get_success_url(self):
        return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.pk})


class ClientUpdateView(AdminCRMManagerMixin, OwnerAssignMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "crm/client_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("owner")

    def get_success_url(self):
        return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.pk})

class ClientDeleteView(AdminCRMManagerMixin, DeleteView):
    model = Client
    template_name = "crm/client_delete.html"
    context_object_name = "client"
    success_url = reverse_lazy("crm:client_list")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("owner")
            .prefetch_related(
                "contacts",
                "leads",
                "reviews",
                "inquiries",
                "deals",
            )
        )

    def form_valid(self, form):
        client_name = self.object.display_name or self.object.name
        messages.success(self.request, f"Client '{client_name}' deleted successfully.")
        return super().form_valid(form)
    
# ============================================================
# Leads
# Access: Admin + CRM Manager only
# ============================================================

class LeadListView(AdminCRMManagerMixin, ListView):
    model = Lead
    template_name = "crm/lead_list.html"
    context_object_name = "leads"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "inquiry", "owner")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(whatsapp__icontains=q)
                | Q(wedding_city__icontains=q)
                | Q(wedding_district__icontains=q)
                | Q(wedding_state__icontains=q)
                | Q(wedding_country__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
                | Q(notes__icontains=q)
            )

        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        source = (self.request.GET.get("source") or "").strip()
        if source:
            qs = qs.filter(source=source)

        return qs


class LeadDetailView(AdminCRMManagerMixin, DetailView):
    model = Lead
    template_name = "crm/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("client", "inquiry", "owner")
            .prefetch_related("inquiries", "deals", "deals__proposals")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["deals"] = self.object.deals.all().order_by("-created_at")

        return context


class LeadCreateView(AdminCRMManagerMixin, OwnerAssignMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def get_initial(self):
        initial = super().get_initial()
        inquiry_id = self.request.GET.get("inquiry")

        if inquiry_id:
            inquiry = Inquiry.objects.filter(pk=inquiry_id).first()

            if inquiry:
                initial.update(
                    {
                        "inquiry": inquiry.pk,
                        "client": inquiry.client_id,
                        "name": inquiry.name,
                        "email": inquiry.email,
                        "phone": inquiry.phone,
                        "whatsapp": inquiry.whatsapp,
                        "source": inquiry.channel,
                        "source_detail": "Converted from inquiry",
                        "notes": inquiry.message,
                        "status": "new",
                    }
                )

        return initial

    @transaction.atomic
    def form_valid(self, form):
        response = super().form_valid(form)

        inquiry = form.cleaned_data.get("inquiry")
        if inquiry:
            inquiry.lead = self.object
            inquiry.status = "converted"
            inquiry.save(update_fields=["lead", "status", "updated_at"])

        return response

    def get_success_url(self):
        return reverse_lazy("crm:lead_detail", kwargs={"pk": self.object.pk})


class LeadUpdateView(AdminCRMManagerMixin, OwnerAssignMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def get_queryset(self):
        return super().get_queryset().select_related("client", "inquiry", "owner")

    def get_success_url(self):
        return reverse_lazy("crm:lead_detail", kwargs={"pk": self.object.pk})


class LeadDeleteView(AdminCRMManagerMixin, DeleteView):
    model = Lead
    template_name = "crm/lead_delete.html"
    context_object_name = "lead"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("client", "inquiry", "owner")
            .prefetch_related("inquiries", "deals")
        )

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})

        return reverse_lazy("crm:lead_list")

    def form_valid(self, form):
        lead_name = self.object.name
        messages.success(self.request, f"Lead '{lead_name}' deleted successfully.")
        return super().form_valid(form)


# ============================================================
# Inquiries
# List/detail/create: Everyone logged in
# Update/delete: Admin + CRM Manager + Project Manager
# Convert to lead: Admin + CRM Manager only
# ============================================================

class InquiryListView(StaffAllMixin, ListView):
    model = Inquiry
    template_name = "crm/inquiry_list.html"
    context_object_name = "inquiries"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("lead", "client", "handled_by", "owner")

        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(whatsapp__icontains=q)
                | Q(message__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
                | Q(handled_by__first_name__icontains=q)
                | Q(handled_by__last_name__icontains=q)
                | Q(handled_by__username__icontains=q)
            )

        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        channel = (self.request.GET.get("channel") or "").strip()
        if channel:
            qs = qs.filter(channel=channel)

        handled_by = (self.request.GET.get("handled_by") or "").strip()
        if handled_by:
            qs = qs.filter(handled_by_id=handled_by)

        return qs


class InquiryDetailView(StaffAllMixin, DetailView):
    model = Inquiry
    template_name = "crm/inquiry_detail.html"
    context_object_name = "inquiry"

    def get_queryset(self):
        return super().get_queryset().select_related("lead", "client", "handled_by", "owner")


class InquiryCreateView(StaffAllMixin, OwnerAssignMixin, CreateView):
    model = Inquiry
    form_class = InquiryForm
    template_name = "crm/inquiry_form.html"
    success_url = reverse_lazy("crm:inquiry_list")


class InquiryUpdateView(InquiryManagerMixin, OwnerAssignMixin, UpdateView):
    model = Inquiry
    form_class = InquiryForm
    template_name = "crm/inquiry_form.html"
    success_url = reverse_lazy("crm:inquiry_list")

    def get_queryset(self):
        return super().get_queryset().select_related("lead", "client", "handled_by", "owner")


class InquiryDeleteView(InquiryManagerMixin, DeleteView):
    model = Inquiry
    template_name = "crm/inquiry_confirm_delete.html"
    success_url = reverse_lazy("crm:inquiry_list")

    def get_queryset(self):
        return super().get_queryset().select_related("lead", "client", "handled_by", "owner")


class InquiryConvertToLeadView(AdminCRMManagerMixin, OwnerAssignMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.inquiry = get_object_or_404(
            Inquiry.objects.select_related("client", "lead", "owner", "handled_by"),
            pk=self.kwargs["pk"],
        )

        if self.inquiry.lead_id:
            messages.info(request, "This inquiry is already converted to a lead.")
            return redirect("crm:lead_detail", pk=self.inquiry.lead_id)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()

        initial.update(
            {
                "inquiry": self.inquiry.pk,
                "client": self.inquiry.client_id,
                "name": self.inquiry.name,
                "email": self.inquiry.email,
                "phone": self.inquiry.phone,
                "whatsapp": self.inquiry.whatsapp,
                "source": self.inquiry.channel,
                "source_detail": "Converted from inquiry",
                "notes": self.inquiry.message,
                "status": "new",
            }
        )

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_inquiry"] = self.inquiry
        context["is_conversion"] = True
        return context

    @transaction.atomic
    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        response = super().form_valid(form)

        self.inquiry.lead = self.object
        self.inquiry.status = "converted"
        self.inquiry.save(update_fields=["lead", "status", "updated_at"])

        messages.success(self.request, "Inquiry converted to lead successfully.")

        return response

    def get_success_url(self):
        return reverse_lazy("crm:lead_detail", kwargs={"pk": self.object.pk})