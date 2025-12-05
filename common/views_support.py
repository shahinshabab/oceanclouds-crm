from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, DetailView

from .models import Ticket, TicketPriority, TicketStatus
from .forms import TicketForm


class TicketListView(LoginRequiredMixin, ListView):
    model = Ticket
    template_name = "common/ticket_list.html"
    context_object_name = "tickets"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        qs = Ticket.objects.filter(created_by=user)

        q = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        priority = self.request.GET.get("priority", "").strip()

        if q:
            qs = qs.filter(
                Q(subject__icontains=q) |
                Q(description__icontains=q)
            )

        if status:
            qs = qs.filter(status=status)

        if priority:
            qs = qs.filter(priority=priority)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "").strip()
        ctx["status_filter"] = self.request.GET.get("status", "").strip()
        ctx["priority_filter"] = self.request.GET.get("priority", "").strip()
        ctx["ticket_status_choices"] = TicketStatus.choices
        ctx["ticket_priority_choices"] = TicketPriority.choices
        return ctx



class TicketCreateView(LoginRequiredMixin, CreateView):
    model = Ticket
    form_class = TicketForm
    template_name = "common/ticket_form.html"
    success_url = reverse_lazy("common:ticket_list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)



class TicketDetailView(LoginRequiredMixin, DetailView):
    model = Ticket
    template_name = "common/ticket_detail.html"
    context_object_name = "ticket"

    def get_queryset(self):
        return Ticket.objects.filter(created_by=self.request.user)
