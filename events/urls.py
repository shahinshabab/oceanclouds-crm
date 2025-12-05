# events/urls.py
from django.urls import path

from . import views

app_name = "events"

urlpatterns = [
    # Venues
    path("venues/", views.VenueListView.as_view(), name="venue_list"),
    path("venues/new/", views.VenueCreateView.as_view(), name="venue_create"),
    path("venues/<int:pk>/", views.VenueDetailView.as_view(), name="venue_detail"),
    path("venues/<int:pk>/edit/", views.VenueUpdateView.as_view(), name="venue_update"),

    # Events
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/new/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_update"),

    # Guests
    path("event-persons/", views.EventPersonListView.as_view(), name="event_person_list"),
    path("event-persons/new/", views.EventPersonCreateView.as_view(), name="event_person_create"),
    path("event-persons/<int:pk>/", views.EventPersonDetailView.as_view(), name="event_person_detail"),
    path("event-persons/<int:pk>/edit/", views.EventPersonUpdateView.as_view(), name="event_person_update"),

    # Checklist
    path("checklist/", views.ChecklistItemListView.as_view(), name="checklist_list"),
    path("checklist/new/", views.ChecklistItemCreateView.as_view(), name="checklist_create"),
    path("checklist/<int:pk>/", views.ChecklistItemDetailView.as_view(), name="checklist_detail"),
    path("checklist/<int:pk>/edit/", views.ChecklistItemUpdateView.as_view(), name="checklist_update"),

    # Event Vendors
    path("event-vendors/", views.EventVendorListView.as_view(), name="event_vendor_list"),
    path("event-vendors/new/", views.EventVendorCreateView.as_view(), name="event_vendor_create"),
    path("event-vendors/<int:pk>/", views.EventVendorDetailView.as_view(), name="event_vendor_detail"),
    path("event-vendors/<int:pk>/edit/", views.EventVendorUpdateView.as_view(), name="event_vendor_update"),

    path("calendar/", views.EventCalendarView.as_view(), name="event_calendar"),
]
