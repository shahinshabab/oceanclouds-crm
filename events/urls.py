# events/urls.py

from django.urls import path
from . import views

app_name = "events"

urlpatterns = [
    # Calendar
    path("calendar/", views.EventCalendarView.as_view(), name="event_calendar"),

    # Venues
    path("venues/", views.VenueListView.as_view(), name="venue_list"),
    path("venues/new/", views.VenueCreateView.as_view(), name="venue_create"),
    path("venues/<int:pk>/", views.VenueDetailView.as_view(), name="venue_detail"),
    path("venues/<int:pk>/edit/", views.VenueUpdateView.as_view(), name="venue_update"),
    path("venues/<int:pk>/delete/", views.VenueDeleteView.as_view(), name="venue_delete"),

    # Events
    path("events/", views.EventListView.as_view(), name="event_list"),
    path("events/new/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<int:pk>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<int:pk>/edit/", views.EventUpdateView.as_view(), name="event_update"),
    path("events/<int:pk>/delete/", views.EventDeleteView.as_view(), name="event_delete"),

    # Event Checklists
    path("checklists/", views.EventChecklistListView.as_view(), name="checklist_list"),
    path("checklists/new/", views.EventChecklistCreateView.as_view(), name="checklist_create"),
    path("checklists/<int:pk>/", views.EventChecklistDetailView.as_view(), name="checklist_detail"),
    path("checklists/<int:pk>/edit/", views.EventChecklistUpdateView.as_view(), name="checklist_update"),
    path("checklists/<int:pk>/delete/", views.EventChecklistDeleteView.as_view(), name="checklist_delete"),

    path("checklist-items/new/", views.ChecklistItemCreateView.as_view(), name="checklist_item_create"),
    path("checklist-items/<int:pk>/edit/", views.ChecklistItemUpdateView.as_view(), name="checklist_item_update"),
    path("checklist-items/<int:pk>/delete/", views.ChecklistItemDeleteView.as_view(), name="checklist_item_delete"),
]