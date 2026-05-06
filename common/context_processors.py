# common/context_processors.py

from common.models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {
            "notifications": [],
            "unread_notification_count": 0,
        }

    unread_qs = Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    )

    return {
        "notifications": unread_qs.select_related("actor", "content_type").order_by("-created_at")[:10],
        "unread_notification_count": unread_qs.count(),
    }