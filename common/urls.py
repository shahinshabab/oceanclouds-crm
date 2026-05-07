# common/urls.py

from django.urls import path
from .views import NotificationListView,mark_notification_read

app_name = "common"

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification_list"),
    path(
        "notifications/<int:pk>/mark-read/",
        mark_notification_read,
        name="notification_mark_read",
    ),
]
