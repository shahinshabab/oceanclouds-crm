from django.db.models import Q
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
    DetailView,
    DeleteView,
)

from .models import Client, Contact, Lead, Inquiry, ClientReview
from .forms import ClientForm, ContactForm, LeadForm, InquiryForm ,ClientReviewForm

# Roles / mixins
from common.mixins import AdminManagerMixin, StaffAllMixin
from common.roles import ROLE_EMPLOYEE, user_has_role

# -------- Client Reviews -------- #

class ClientReviewListView(AdminManagerMixin, ListView):
    model = ClientReview
    template_name = "crm/review_list.html"
    context_object_name = "reviews"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client", "owner")

        # Search query
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(comment__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
                | Q(next_action__icontains=q)
            )

        # Filter by client (if you ever add it to the UI)
        client_id = (self.request.GET.get("client") or "").strip()
        if client_id:
            qs = qs.filter(client_id=client_id)

        # Filter by rating
        rating = (self.request.GET.get("rating") or "").strip()
        if rating.isdigit():
            qs = qs.filter(rating=int(rating))

        # NEW: Filter by action due status (based on next_action_date)
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




class ClientReviewDetailView(AdminManagerMixin, DetailView):
    model = ClientReview
    template_name = "crm/review_detail.html"
    context_object_name = "review"



class ClientReviewCreateView(AdminManagerMixin, CreateView):
    model = ClientReview
    form_class = ClientReviewForm
    template_name = "crm/review_form.html"

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")
        if client_id:
            initial["client"] = client_id
        return initial

    def form_valid(self, form):
        # Set owner
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})
        return reverse_lazy("crm:review_list")


class ClientReviewUpdateView(AdminManagerMixin, UpdateView):
    model = ClientReview
    form_class = ClientReviewForm
    template_name = "crm/review_form.html"

    def form_valid(self, form):
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})
        return reverse_lazy("crm:review_list")


    
# -------- Contacts -------- #

class ContactListView(AdminManagerMixin, ListView):
    model = Contact
    template_name = "crm/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client")

        # Search: by name or email (also client's name)
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(last_name__icontains=q)
                | Q(email__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
            )

        # Filter 1: role (bride, groom, parent, etc.)
        role = (self.request.GET.get("role") or "").strip()
        if role:
            qs = qs.filter(role=role)

        # Filter 2: is_primary (1 = primary only, 0 = non-primary only)
        is_primary = (self.request.GET.get("is_primary") or "").strip()
        if is_primary == "1":
            qs = qs.filter(is_primary=True)
        elif is_primary == "0":
            qs = qs.filter(is_primary=False)

        return qs


class ContactDetailView(AdminManagerMixin, DetailView):
    model = Contact
    template_name = "crm/contact_detail.html"
    context_object_name = "contact"


class ContactCreateView(AdminManagerMixin, CreateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def get_initial(self):
        initial = super().get_initial()
        client_id = self.request.GET.get("client")
        if client_id:
            initial["client"] = client_id
        return initial

    def form_valid(self, form):
        # Owned mixin: assign owner if needed
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """
        If this contact belongs to a client, go back to that client's page.
        Otherwise fall back to contact list.
        """
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})
        return reverse_lazy("crm:contact_list")


class ContactUpdateView(AdminManagerMixin, UpdateView):
    model = Contact
    form_class = ContactForm
    template_name = "crm/contact_form.html"

    def form_valid(self, form):
        # Keep behaviour consistent with create
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        if self.object.client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": self.object.client_id})
        return reverse_lazy("crm:contact_list")


class ContactDeleteView(AdminManagerMixin, DeleteView):
    model = Contact
    template_name = "crm/contact_confirm_delete.html"

    def get_success_url(self):
        # After deleting, send back to related client if available
        client_id = self.object.client_id
        if client_id:
            return reverse_lazy("crm:client_detail", kwargs={"pk": client_id})
        return reverse_lazy("crm:contact_list")


# -------- Clients -------- #

class ClientListView(AdminManagerMixin, ListView):
    model = Client
    template_name = "crm/client_list.html"
    context_object_name = "clients"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        # Search: by name/display name or email/phone
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(display_name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
            )

        # Filter 1: is_active (1 = active, 0 = inactive)
        is_active = (self.request.GET.get("is_active") or "").strip()
        if is_active == "1":
            qs = qs.filter(is_active=True)
        elif is_active == "0":
            qs = qs.filter(is_active=False)

        # Filter 2: country
        country = (self.request.GET.get("country") or "").strip()
        if country:
            qs = qs.filter(country__iexact=country)

        return qs


class ClientDetailView(AdminManagerMixin, DetailView):
    model = Client
    template_name = "crm/client_detail.html"
    context_object_name = "client"


class ClientCreateView(AdminManagerMixin, CreateView):
    model = Client
    form_class = ClientForm
    template_name = "crm/client_form.html"
    success_url = reverse_lazy("crm:client_list")

    def form_valid(self, form):
        # Owned mixin: assign owner if needed
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)


class ClientUpdateView(AdminManagerMixin, UpdateView):
    model = Client
    form_class = ClientForm
    template_name = "crm/client_form.html"
    success_url = reverse_lazy("crm:client_list")


# -------- Leads -------- #

class LeadListView(AdminManagerMixin, ListView):
    model = Lead
    template_name = "crm/lead_list.html"
    context_object_name = "leads"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("client")

        # Search: by name, email, phone, whatsapp, wedding location, or client name
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(whatsapp__icontains=q)
                | Q(wedding_city__icontains=q)
                | Q(wedding_district__icontains=q)
                | Q(client__name__icontains=q)
                | Q(client__display_name__icontains=q)
            )

        # Filter 1: status (new, contacted, qualified, etc.)
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        # Filter 2: source (website, instagram, whatsapp, referral, etc.)
        source = (self.request.GET.get("source") or "").strip()
        if source:
            qs = qs.filter(source=source)

        return qs


class LeadDetailView(AdminManagerMixin, DetailView):
    model = Lead
    template_name = "crm/lead_detail.html"
    context_object_name = "lead"


class LeadCreateView(AdminManagerMixin, CreateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"
    success_url = reverse_lazy("crm:lead_list")

    def form_valid(self, form):
        # Owned mixin: assign owner if needed
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user
        return super().form_valid(form)


class LeadUpdateView(AdminManagerMixin, UpdateView):
    model = Lead
    form_class = LeadForm
    template_name = "crm/lead_form.html"
    success_url = reverse_lazy("crm:lead_list")


# -------- Inquiries -------- #

class InquiryListView(StaffAllMixin, ListView):
    model = Inquiry
    template_name = "crm/inquiry_list.html"
    context_object_name = "inquiries"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("lead", "client", "handled_by")

        # Employees only see their own inquiries
        user = self.request.user
        if user_has_role(user, ROLE_EMPLOYEE) and not user.is_superuser:
            qs = qs.filter(handled_by=user)

        # Search: by inquirer name, email, phone, or wedding location
        q = (self.request.GET.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(email__icontains=q)
                | Q(phone__icontains=q)
                | Q(wedding_city__icontains=q)
                | Q(wedding_district__icontains=q)
            )

        # Filter 1: status (open, in_progress, closed, converted)
        status = (self.request.GET.get("status") or "").strip()
        if status:
            qs = qs.filter(status=status)

        # Filter 2: channel (website, phone, whatsapp, etc.)
        channel = (self.request.GET.get("channel") or "").strip()
        if channel:
            qs = qs.filter(channel=channel)

        return qs


class InquiryDetailView(StaffAllMixin, DetailView):
    model = Inquiry
    template_name = "crm/inquiry_detail.html"
    context_object_name = "inquiry"

    def get_queryset(self):
        qs = super().get_queryset().select_related("lead", "client", "handled_by")

        # Employees can only open details for their own inquiries
        user = self.request.user
        if user_has_role(user, ROLE_EMPLOYEE) and not user.is_superuser:
            qs = qs.filter(handled_by=user)

        return qs


class InquiryCreateView(StaffAllMixin, CreateView):
    model = Inquiry
    form_class = InquiryForm
    template_name = "crm/inquiry_form.html"
    success_url = reverse_lazy("crm:inquiry_list")

    def form_valid(self, form):
        # DO NOT set handled_by to current user anymore.
        # It must always be one of the managers from the form.

        # Set owner if Inquiry uses Owned
        if hasattr(form.instance, "owner") and not form.instance.owner_id:
            form.instance.owner = self.request.user

        return super().form_valid(form)


class InquiryUpdateView(StaffAllMixin, UpdateView):
    model = Inquiry
    form_class = InquiryForm
    template_name = "crm/inquiry_form.html"
    success_url = reverse_lazy("crm:inquiry_list")

    def get_queryset(self):
        qs = super().get_queryset().select_related("lead", "client", "handled_by")

        # Employees can only edit their own inquiries
        user = self.request.user
        if user_has_role(user, ROLE_EMPLOYEE) and not user.is_superuser:
            qs = qs.filter(handled_by=user)

        return qs
