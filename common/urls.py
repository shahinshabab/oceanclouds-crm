# common/urls.py

from django.urls import path
from .views_support import TicketListView, TicketCreateView, TicketDetailView
from .views import NotificationListView, mark_notification_read

app_name = "common"

urlpatterns = [
    path("tickets/", TicketListView.as_view(), name="ticket_list"),
    path("tickets/new/", TicketCreateView.as_view(), name="ticket_create"),
    path("tickets/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/<int:pk>/mark-read/",
        mark_notification_read,
        name="notification_mark_read",
    ),
]
