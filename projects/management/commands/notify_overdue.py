# common/management/commands/notify_overdue.py

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.utils import timezone

from common.notifications import create_notification
from common.models import Notification  # adjust import
from projects.models import Task, Deliverable  # adjust as needed
from projects.models import TaskStatus, DeliverableStatus  # your TextChoices


class Command(BaseCommand):
    help = "Create overdue notifications for tasks and deliverables."

    def handle(self, *args, **options):
        today = timezone.localdate()

        self.stdout.write("Checking overdue tasks...")
        self._notify_overdue_tasks(today)

        self.stdout.write("Checking overdue deliverables...")
        self._notify_overdue_deliverables(today)

        self.stdout.write(self.style.SUCCESS("Overdue notifications processed."))

    def _notify_overdue_tasks(self, today):
        ct_task = ContentType.objects.get_for_model(Task)

        overdue_tasks = (
            Task.objects.filter(
                due_date__lt=today,
                status__in=[
                    TaskStatus.PENDING,
                    TaskStatus.IN_PROGRESS,
                    TaskStatus.BLOCKED,
                ],
            )
            .select_related("assigned_to")
        )

        for task in overdue_tasks:
            if not task.assigned_to:
                continue

            # Avoid duplicate unread overdue notification for same task & user
            exists = Notification.objects.filter(
                recipient=task.assigned_to,
                notif_type=Notification.Type.OVERDUE,
                content_type=ct_task,
                object_id=task.pk,
                is_read=False,
            ).exists()
            if exists:
                continue

            create_notification(
                recipient=task.assigned_to,
                notif_type=Notification.Type.OVERDUE,
                target=task,
                message=f"Task '{task}' is overdue.",
            )

    def _notify_overdue_deliverables(self, today):
        ct_deliv = ContentType.objects.get_for_model(Deliverable)

        overdue_deliverables = (
            Deliverable.objects.filter(
                due_date__lt=today,
                status__in=[
                    DeliverableStatus.PENDING,
                    DeliverableStatus.IN_PROGRESS,
                ],
            )
            .select_related("assigned_to", "project__manager")
        )

        for d in overdue_deliverables:
            # choose owner of the overdue deliverable
            recipient = None
            if hasattr(d, "assigned_to") and d.assigned_to:
                recipient = d.assigned_to
            elif d.project and d.project.manager:
                recipient = d.project.manager

            if not recipient:
                continue

            exists = Notification.objects.filter(
                recipient=recipient,
                notif_type=Notification.Type.DELIVERABLE_OVERDUE,
                content_type=ct_deliv,
                object_id=d.pk,
                is_read=False,
            ).exists()
            if exists:
                continue

            create_notification(
                recipient=recipient,
                notif_type=Notification.Type.DELIVERABLE_OVERDUE,
                target=d,
                message=f"Deliverable '{d}' is overdue.",
            )
