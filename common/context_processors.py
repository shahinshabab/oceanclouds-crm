# common/context_processors.py
from .models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {"notifications": []}

    qs = (
        Notification.objects
        .filter(recipient=request.user, is_read=False)
        .order_by("-created_at")[:10]
    )

    return {"notifications": qs}
