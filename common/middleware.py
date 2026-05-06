# common/middleware.py

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from .models import UserLoginSession, UserSessionEndReason


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