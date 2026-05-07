# common/middleware.py

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import UserLoginSession, UserSessionEndReason
from urllib.parse import urlparse

from django.contrib.messages import get_messages

class CloseExpiredLoginSessionsMiddleware:
    """
    Closes login sessions that passed SESSION_COOKIE_AGE.

    Django session expiry does not automatically call user_logged_out,
    so this middleware records auto-timeout sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_age = getattr(settings, "SESSION_COOKIE_AGE", 10 * 60 * 60)
        cutoff = timezone.now() - timedelta(seconds=max_age)

        UserLoginSession.objects.filter(
            logout_at__isnull=True,
            login_at__lt=cutoff,
        ).update(
            logout_at=timezone.now(),
            end_reason=UserSessionEndReason.AUTO_TIMEOUT,
        )

        return self.get_response(request)


class ClearFrontendMessagesBeforeAdminMiddleware:
    """
    Clear pending frontend messages when opening /admin/
    from a non-admin page.

    This prevents app messages like:
    'Event updated successfully'
    from appearing in Django admin.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_admin_path = request.path.startswith("/admin/")

        referer = request.META.get("HTTP_REFERER", "")
        referer_path = urlparse(referer).path if referer else ""

        came_from_admin = referer_path.startswith("/admin/")

        if is_admin_path and not came_from_admin:
            # Iterating get_messages(request) consumes pending messages.
            list(get_messages(request))

        return self.get_response(request)