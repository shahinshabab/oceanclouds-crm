# common/middleware.py

from urllib.parse import urlparse

from django.contrib.messages import get_messages
from django.contrib.sessions.models import Session
from datetime import timedelta

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from common.models import UserLoginSession, UserSessionEndReason
from projects.utils import pause_active_work_sessions_for_user


class CloseExpiredLoginSessionsMiddleware:
    """
    Closes login sessions that passed SESSION_COOKIE_AGE.

    Also pauses active project work sessions for the same user,
    so task/deliverable timers do not keep running after auto logout.

    Important:
    We pause the work session, not end it.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        max_age = getattr(settings, "SESSION_COOKIE_AGE", 10 * 60 * 60)
        now = timezone.now()
        cutoff = now - timedelta(seconds=max_age)

        active_login_sessions = UserLoginSession.objects.filter(
            logout_at__isnull=True,
        )
        active_session_keys = list(
            active_login_sessions.values_list("session_key", flat=True).distinct()
        )
        valid_session_keys = set(
            Session.objects.filter(
                session_key__in=active_session_keys,
                expire_date__gt=now,
            ).values_list("session_key", flat=True)
        )
        stale_session_keys = [
            session_key
            for session_key in active_session_keys
            if session_key not in valid_session_keys
        ]

        expired_login_sessions = list(
            UserLoginSession.objects
            .filter(
                logout_at__isnull=True,
            )
            .filter(
                Q(login_at__lt=cutoff)
                | Q(session_key__in=stale_session_keys)
            )
            .select_related("user")
        )

        expired_user_ids = {
            session.user_id
            for session in expired_login_sessions
        }

        for login_session in expired_login_sessions:
            login_session.logout_at = now
            login_session.end_reason = UserSessionEndReason.AUTO_TIMEOUT
            login_session.save(update_fields=["logout_at", "end_reason"])

        for user_id in expired_user_ids:
            pause_active_work_sessions_for_user(user_id)

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
