from datetime import timedelta

from django.contrib.auth.models import Group, Permission
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from common.role_permissions import setup_role_groups
from common.roles import ROLE_ADMIN, ROLE_CRM_MANAGER, ROLE_EMPLOYEE, ROLE_PROJECT_MANAGER
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


class RolePermissionSetupTests(TestCase):
    def test_setup_role_groups_creates_expected_groups(self):
        Group.objects.create(name="Manager")

        setup_role_groups()

        self.assertTrue(Group.objects.filter(name=ROLE_ADMIN).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_CRM_MANAGER).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_PROJECT_MANAGER).exists())
        self.assertTrue(Group.objects.filter(name=ROLE_EMPLOYEE).exists())
        self.assertFalse(Group.objects.filter(name="Manager").exists())

    def test_setup_role_groups_assigns_suitable_permissions(self):
        setup_role_groups()

        admin = Group.objects.get(name=ROLE_ADMIN)
        crm_manager = Group.objects.get(name=ROLE_CRM_MANAGER)
        project_manager = Group.objects.get(name=ROLE_PROJECT_MANAGER)
        employee = Group.objects.get(name=ROLE_EMPLOYEE)

        add_client = Permission.objects.get(
            content_type__app_label="crm",
            codename="add_client",
        )
        add_service = Permission.objects.get(
            content_type__app_label="services",
            codename="add_service",
        )
        change_project = Permission.objects.get(
            content_type__app_label="projects",
            codename="change_project",
        )
        view_project = Permission.objects.get(
            content_type__app_label="projects",
            codename="view_project",
        )

        self.assertIn(add_service, admin.permissions.all())
        self.assertIn(add_client, crm_manager.permissions.all())
        self.assertNotIn(add_service, crm_manager.permissions.all())
        self.assertIn(change_project, project_manager.permissions.all())
        self.assertIn(view_project, employee.permissions.all())
        self.assertNotIn(change_project, employee.permissions.all())
