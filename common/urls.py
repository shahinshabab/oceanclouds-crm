# common/urls.py

from django.urls import path
from .views_support import TicketListView, TicketCreateView, TicketDetailView
from .views import NotificationListView,mark_notification_read,analytics_report,analytics_report_pdf,project_report,project_report_pdf

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
    path(
        "analytics/",
        analytics_report,
        name="analytics_report",
    ),
    path(
        "analytics/pdf/",
        analytics_report_pdf,
        name="analytics_report_pdf",
    ),
    path("report/", project_report, name="project_report"),
    path("report/pdf/", project_report_pdf, name="project_report_pdf"),
]
