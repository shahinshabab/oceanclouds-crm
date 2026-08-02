# common/middleware.py

from urllib.parse import urlparse

from django.contrib.auth import logout as auth_logout
from django.contrib.messages import get_messages
from django.contrib.sessions.models import Session
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from common.models import UserLoginSession, UserSessionEndReason
from projects.utils import pause_active_work_sessions_for_user


class CloseExpiredLoginSessionsMiddleware:
    """
    Closes login sessions after the configured inactivity period.

    The login is closed at the timeout boundary. Active task/deliverable work
    is paused at the user's last recorded activity, so the idle window is not
    counted as worked time.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        now = timezone.now()
        idle_seconds = int(
            getattr(settings, "AUTO_LOGOUT_IDLE_SECONDS", 3 * 60 * 60)
        )
        idle_delta = timedelta(seconds=idle_seconds)
        cutoff = now - idle_delta

        timed_out_sessions = list(
            UserLoginSession.objects
            .filter(
                logout_at__isnull=True,
                last_activity_at__lte=cutoff,
            )
            .select_related("user")
        )
        timed_out_keys = {session.session_key for session in timed_out_sessions}

        for login_session in timed_out_sessions:
            login_session.logout_at = login_session.last_activity_at + idle_delta
            login_session.end_reason = UserSessionEndReason.AUTO_TIMEOUT
            login_session.save(update_fields=["logout_at", "end_reason"])

        if timed_out_keys:
            Session.objects.filter(session_key__in=timed_out_keys).delete()

        for login_session in timed_out_sessions:
            user_still_active = UserLoginSession.objects.filter(
                user_id=login_session.user_id,
                logout_at__isnull=True,
            ).exists()
            if not user_still_active:
                pause_active_work_sessions_for_user(
                    login_session.user_id,
                    paused_at=login_session.last_activity_at,
                )

        current_session_key = request.session.session_key
        if (
            current_session_key in timed_out_keys
            and request.user.is_authenticated
        ):
            auth_logout(request)

        response = self.get_response(request)

        if request.user.is_authenticated and request.session.session_key:
            UserLoginSession.objects.filter(
                user_id=request.user.pk,
                session_key=request.session.session_key,
                logout_at__isnull=True,
            ).update(last_activity_at=timezone.now())

        return response


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
