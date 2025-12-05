# events/views.py
from datetime import date, timedelta

from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
)

from common.mixins import AdminManagerMixin, StaffAllMixin

from services.models import Service

from .models import (
    Venue,
    Event,
    EventPerson,
    ChecklistItem,
    EventVendor,
    EventType,
    EventStatus,
    ChecklistCategory,
)
from .forms import (
    VenueForm,
    EventForm,
    EventPersonForm,
    ChecklistItemForm,
    EventVendorForm,
)


# -------------------------------------------------------------------
# Calendar
# -------------------------------------------------------------------

class EventCalendarView(StaffAllMixin, TemplateView):
    template_name = "events/event_calendar.html"

    TIME_START = 8   # 8 AM
    TIME_END = 22    # 10 PM

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # -------- Filters from query params -------- #
        range_param = (request.GET.get("range") or "1m").strip()  # "1m", "2m", "3m"
        event_type = (request.GET.get("event_type") or "").strip()
        status = (request.GET.get("status") or "").strip()

        # -------- Date range (starting today) -------- #
        today = date.today()
        days_map = {
            "1m": 30,
            "2m": 60,
            "3m": 90,
        }
        days = days_map.get(range_param, 30)
        end_date = today + timedelta(days=days - 1)

        qs = (
            Event.objects
            .filter(date__range=(today, end_date))
            .select_related("client", "venue")
        )

        if event_type:
            qs = qs.filter(event_type=event_type)
        if status:
            qs = qs.filter(status=status)

        # Build date list
        dates = []
        current = today
        while current <= end_date:
            dates.append(current)
            current += timedelta(days=1)

        time_slots = list(range(self.TIME_START, self.TIME_END + 1))

        # Map events by date + hour
        events_by_date_hour = {
            d: {h: [] for h in time_slots}
            for d in dates
        }

        for ev in qs:
            if ev.start_time:
                h = ev.start_time.hour
                if h < self.TIME_START or h > self.TIME_END:
                    h = self.TIME_START
            else:
                h = self.TIME_START

            if ev.date in events_by_date_hour:
                events_by_date_hour[ev.date][h].append(ev)

        # Build rows: one per hour, with cells per date
        time_rows = []
        for hour in time_slots:
            cells = []
            for d in dates:
                cells.append(
                    {
                        "date": d,
                        "events": events_by_date_hour[d][hour],
                    }
                )
            time_rows.append(
                {
                    "hour": hour,
                    "cells": cells,
                }
            )

        context.update(
            {
                "dates": dates,
                "time_rows": time_rows,
                "time_slots": time_slots,
                "event_type": event_type,
                "range_param": range_param,
                "status": status,
                "event_type_choices": EventType.choices,
                "status_choices": EventStatus.choices,
            }
        )
        return context


# -------------------------------------------------------------------
# Venues
# -------------------------------------------------------------------

class VenueListView(AdminManagerMixin, ListView):
    model = Venue
    template_name = "events/venue_list.html"
    context_object_name = "venues"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()

        q = (self.request.GET.get("q") or "").strip()
        venue_type = (self.request.GET.get("venue_type") or "").strip()
        city = (self.request.GET.get("city") or "").strip()

        if venue_type:
            qs = qs.filter(venue_type=venue_type)
        if city:
            qs = qs.filter(city__iexact=city)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(city__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["venue_type"] = self.request.GET.get("venue_type", "")
        context["city"] = self.request.GET.get("city", "")
        context["city_filter"] = (self.request.GET.get("city") or "").strip()
        context["venue_type_choices"] = Venue._meta.get_field("venue_type").choices
        return context


class VenueDetailView(AdminManagerMixin, DetailView):
    model = Venue
    template_name = "events/venue_detail.html"
    context_object_name = "venue"


class VenueCreateView(AdminManagerMixin, CreateView):
    model = Venue
    form_class = VenueForm
    template_name = "events/venue_form.html"
    success_url = reverse_lazy("events:venue_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class VenueUpdateView(AdminManagerMixin, UpdateView):
    model = Venue
    form_class = VenueForm
    template_name = "events/venue_form.html"
    success_url = reverse_lazy("events:venue_list")


# -------------------------------------------------------------------
# Events
# -------------------------------------------------------------------

class EventListView(AdminManagerMixin, ListView):
    model = Event
    template_name = "events/event_list.html"
    context_object_name = "events"
    paginate_by = 20

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("client", "primary_contact", "venue")
        )

        q = (self.request.GET.get("q") or "").strip()
        event_type = (self.request.GET.get("event_type") or "").strip()
        status = (self.request.GET.get("status") or "").strip()

        if event_type:
            qs = qs.filter(event_type=event_type)
        if status:
            qs = qs.filter(status=status)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(client__name__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["event_type"] = self.request.GET.get("event_type", "")
        context["status"] = self.request.GET.get("status", "")
        context["event_type_choices"] = EventType.choices
        context["status_choices"] = EventStatus.choices
        return context


class EventDetailView(StaffAllMixin, DetailView):
    model = Event
    template_name = "events/event_detail.html"
    context_object_name = "event"


class EventCreateView(AdminManagerMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_url = reverse_lazy("events:event_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class EventUpdateView(AdminManagerMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    success_url = reverse_lazy("events:event_list")


# -------------------------------------------------------------------
# Event People (Bride / Groom / Key people)
# -------------------------------------------------------------------

class EventPersonListView(AdminManagerMixin, ListView):
    model = EventPerson
    template_name = "events/event_person_list.html"
    context_object_name = "people"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("event")

        q = (self.request.GET.get("q") or "").strip()
        role = (self.request.GET.get("role") or "").strip()
        event_id = (self.request.GET.get("event") or "").strip()

        if role:
            qs = qs.filter(role=role)
        if event_id:
            qs = qs.filter(event_id=event_id)

        if q:
            qs = qs.filter(
                Q(full_name__icontains=q) |
                Q(email__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["role"] = (self.request.GET.get("role") or "").strip()
        context["event_filter"] = (self.request.GET.get("event") or "").strip()
        context["role_choices"] = EventPerson._meta.get_field("role").choices
        context["event_choices"] = Event.objects.order_by("date", "name")
        return context


class EventPersonDetailView(AdminManagerMixin, DetailView):
    model = EventPerson
    template_name = "events/event_person_detail.html"
    context_object_name = "person"


class EventPersonCreateView(AdminManagerMixin, CreateView):
    model = EventPerson
    form_class = EventPersonForm
    template_name = "events/event_person_form.html"
    success_url = reverse_lazy("events:event_person_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class EventPersonUpdateView(AdminManagerMixin, UpdateView):
    model = EventPerson
    form_class = EventPersonForm
    template_name = "events/event_person_form.html"
    success_url = reverse_lazy("events:event_person_list")


# -------------------------------------------------------------------
# Checklist Items
# -------------------------------------------------------------------

class ChecklistItemListView(AdminManagerMixin, ListView):
    model = ChecklistItem
    template_name = "events/checklist_list.html"
    context_object_name = "checklist_items"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("event", "assigned_to", "vendor")

        q = (self.request.GET.get("q") or "").strip()
        category = (self.request.GET.get("category") or "").strip()
        is_done = (self.request.GET.get("is_done") or "").strip()

        if category:
            qs = qs.filter(category=category)

        if is_done in ("true", "false", "1", "0"):
            value = is_done in ("true", "1")
            qs = qs.filter(is_done=value)

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(event__name__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["category"] = (self.request.GET.get("category") or "").strip()
        context["is_done"] = (self.request.GET.get("is_done") or "").strip()
        context["category_choices"] = ChecklistCategory.choices
        context["event_choices"] = Event.objects.order_by("date", "name")
        return context


class ChecklistItemDetailView(AdminManagerMixin, DetailView):
    model = ChecklistItem
    template_name = "events/checklist_detail.html"
    context_object_name = "item"


class ChecklistItemCreateView(AdminManagerMixin, CreateView):
    model = ChecklistItem
    form_class = ChecklistItemForm
    template_name = "events/checklist_form.html"
    success_url = reverse_lazy("events:checklist_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class ChecklistItemUpdateView(AdminManagerMixin, UpdateView):
    model = ChecklistItem
    form_class = ChecklistItemForm
    template_name = "events/checklist_form.html"
    success_url = reverse_lazy("events:checklist_list")


# -------------------------------------------------------------------
# Event Vendors
# -------------------------------------------------------------------

class EventVendorListView(AdminManagerMixin, ListView):
    model = EventVendor
    template_name = "events/event_vendor_list.html"
    context_object_name = "event_vendors"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset().select_related("event", "vendor", "service")

        q = (self.request.GET.get("q") or "").strip()
        is_confirmed = (self.request.GET.get("is_confirmed") or "").strip()
        service_id = (self.request.GET.get("service") or "").strip()

        if is_confirmed in ("true", "false", "1", "0"):
            value = is_confirmed in ("true", "1")
            qs = qs.filter(is_confirmed=value)

        if service_id:
            qs = qs.filter(service_id=service_id)

        if q:
            qs = qs.filter(
                Q(event__name__icontains=q) |
                Q(vendor__name__icontains=q)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = (self.request.GET.get("q") or "").strip()
        context["is_confirmed"] = (self.request.GET.get("is_confirmed") or "").strip()
        context["service_filter"] = (self.request.GET.get("service") or "").strip()
        context["service_choices"] = Service.objects.order_by("name")
        return context


class EventVendorDetailView(AdminManagerMixin, DetailView):
    model = EventVendor
    template_name = "events/event_vendor_detail.html"
    context_object_name = "event_vendor"


class EventVendorCreateView(AdminManagerMixin, CreateView):
    model = EventVendor
    form_class = EventVendorForm
    template_name = "events/event_vendor_form.html"
    success_url = reverse_lazy("events:event_vendor_list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class EventVendorUpdateView(AdminManagerMixin, UpdateView):
    model = EventVendor
    form_class = EventVendorForm
    template_name = "events/event_vendor_form.html"
    success_url = reverse_lazy("events:event_vendor_list")
