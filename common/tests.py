from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from common.test_helpers import AuthenticatedViewTestMixin, make_user
from common.notifications import notify_user

from .models import Choice, Communication, Notification, UserLoginSession


class CommonModelTests(AuthenticatedViewTestMixin):
    list_url_names = ["common:notification_list"]

    def test_choice_string_and_unique_type_value(self):
        Choice.objects.create(type="lead_source", value="Instagram")

        with self.assertRaises(IntegrityError):
            Choice.objects.create(type="lead_source", value="Instagram")

    def test_communication_string_uses_channel_display(self):
        communication = Communication.objects.create(
            channel="email",
            subject="Welcome",
        )

        self.assertEqual(str(communication), "Email - Welcome")

    def test_notification_target_url_uses_target_absolute_url(self):
        recipient = make_user(username="notify-user")
        choice = Choice.objects.create(type="source", value="Website")
        notification = Notification.objects.create(
            recipient=recipient,
            notif_type=Notification.Type.LEAD_FOLLOW_UP,
            target=choice,
            message="Follow up",
        )

        self.assertEqual(str(notification), "Follow up")
        self.assertEqual(notification.get_target_url(), "#")

    def test_notification_dedupe_key_is_unique_per_recipient(self):
        recipient = make_user(username="dedupe-user")
        Notification.objects.create(
            recipient=recipient,
            notif_type=Notification.Type.TASK_DUE,
            dedupe_key="task:1",
        )

        with self.assertRaises(IntegrityError):
            Notification.objects.create(
                recipient=recipient,
                notif_type=Notification.Type.TASK_DUE,
                dedupe_key="task:1",
            )

    def test_duplicate_notifications_get_unique_dedupe_keys(self):
        recipient = make_user(username="duplicate-notify-user")
        choice = Choice.objects.create(type="source", value="Referral")

        first = notify_user(
            recipient=recipient,
            notif_type=Notification.Type.PROJECT_ASSIGNED,
            target=choice,
            message="Assigned once",
            allow_duplicate=True,
        )
        second = notify_user(
            recipient=recipient,
            notif_type=Notification.Type.PROJECT_ASSIGNED,
            target=choice,
            message="Assigned again",
            allow_duplicate=True,
        )

        self.assertIsNotNone(first.dedupe_key)
        self.assertIsNotNone(second.dedupe_key)
        self.assertNotEqual(first.dedupe_key, second.dedupe_key)

    def test_login_session_duration_and_close(self):
        user = make_user(username="session-user")
        session = UserLoginSession.objects.create(
            user=user,
            session_key="abc",
            login_at=timezone.now() - timedelta(hours=2),
        )

        self.assertTrue(session.is_active)
        self.assertGreaterEqual(session.duration_seconds, 7200)

        session.close()
        session.refresh_from_db()
        self.assertFalse(session.is_active)
        self.assertEqual(session.end_reason, "logout")

    def test_mark_notification_read_url_reverses(self):
        recipient = make_user(username="mark-read-user")
        notification = Notification.objects.create(
            recipient=recipient,
            notif_type=Notification.Type.EVENT_REMINDER,
        )

        self.assertEqual(
            reverse("common:notification_mark_read", args=[notification.pk]),
            f"/common/notifications/{notification.pk}/mark-read/",
        )
