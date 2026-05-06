# common/signals.py

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import UserLoginSession, UserSessionEndReason


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


@receiver(user_logged_in)
def record_user_login(sender, request, user, **kwargs):
    if not request.session.session_key:
        request.session.save()

    session_key = request.session.session_key

    UserLoginSession.objects.filter(
        user=user,
        session_key=session_key,
        logout_at__isnull=True,
    ).update(
        logout_at=timezone.now(),
        end_reason=UserSessionEndReason.SYSTEM,
    )

    UserLoginSession.objects.create(
        user=user,
        session_key=session_key,
        login_at=timezone.now(),
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )


@receiver(user_logged_out)
def record_user_logout(sender, request, user, **kwargs):
    if not user or not request:
        return

    session_key = request.session.session_key

    UserLoginSession.objects.filter(
        user=user,
        session_key=session_key,
        logout_at__isnull=True,
    ).update(
        logout_at=timezone.now(),
        end_reason=UserSessionEndReason.LOGOUT,
    )