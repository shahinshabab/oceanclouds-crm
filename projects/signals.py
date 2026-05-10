# projects/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from common.models import Notification
from common.notifications import notify_user
from todos.models import TodoPriority
from todos.services import create_todo_once
from projects.models import Project, Task, Deliverable, ProjectStatus


@receiver(pre_save, sender=Project)
def cache_old_project_values(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_manager_id = None
        instance._old_status = None
        return

    old = sender.objects.filter(pk=instance.pk).only("manager", "status").first()

    instance._old_manager_id = old.manager_id if old else None
    instance._old_status = old.status if old else None


@receiver(post_save, sender=Project)
def notify_and_todo_project_changes(sender, instance, created, **kwargs):
    old_manager_id = getattr(instance, "_old_manager_id", None)
    old_status = getattr(instance, "_old_status", None)

    # Project assigned to project manager
    if instance.manager_id and (created or old_manager_id != instance.manager_id):
        actor = getattr(instance, "owner", None)

        notify_user(
            recipient=instance.manager,
            actor=actor,
            notif_type=Notification.Type.PROJECT_ASSIGNED,
            target=instance,
            message=f"You have been assigned to project: {instance.name}",
        )

        create_todo_once(
            title=f"Review assigned project: {instance.name}",
            description=(
                "You have been assigned as the project manager. "
                "Please review the project details, dates, tasks and deliverables."
            ),
            owner=actor or instance.manager,
            assigned_to=instance.manager,
            priority=TodoPriority.HIGH,
            due_date=instance.start_date,
            project=instance,
            client=instance.client,
            deal=instance.deal,
        )

    # Project completed -> CRM review pending
    if (
        not created
        and old_status != ProjectStatus.COMPLETED
        and instance.status == ProjectStatus.COMPLETED
    ):
        recipient = _resolve_project_review_recipient(instance)

        if recipient:
            notify_user(
                recipient=recipient,
                actor=instance.manager,
                notif_type=Notification.Type.PROJECT_COMPLETED_REVIEW_PENDING,
                target=instance,
                message=f"Project completed. Client review pending: {instance.name}",
            )

            create_todo_once(
                title=f"Collect client review: {instance.name}",
                description="Project is completed. Please contact the client and collect review/feedback.",
                owner=instance.manager or recipient,
                assigned_to=recipient,
                priority=TodoPriority.MEDIUM,
                due_date=None,
                project=instance,
                client=instance.client,
                deal=instance.deal,
            )


def _resolve_project_review_recipient(project):
    deal = getattr(project, "deal", None)
    client = getattr(project, "client", None)

    if deal:
        if getattr(deal, "owner_id", None):
            return deal.owner

        lead = getattr(deal, "lead", None)
        if lead and getattr(lead, "owner_id", None):
            return lead.owner

    if client and getattr(client, "owner_id", None):
        return client.owner

    return getattr(project, "manager", None)


@receiver(pre_save, sender=Task)
def cache_old_task_assignee(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to_id = None
        return

    old = sender.objects.filter(pk=instance.pk).only("assigned_to").first()
    instance._old_assigned_to_id = old.assigned_to_id if old else None


@receiver(post_save, sender=Task)
def notify_and_todo_task_assigned(sender, instance, created, **kwargs):
    if not instance.assigned_to_id:
        return

    old_assigned_to_id = getattr(instance, "_old_assigned_to_id", None)

    if not created and old_assigned_to_id == instance.assigned_to_id:
        return

    actor = getattr(instance.project, "manager", None) or getattr(instance, "owner", None)

    notify_user(
        recipient=instance.assigned_to,
        actor=actor,
        notif_type=Notification.Type.TASK_ASSIGNED,
        target=instance,
        message=f"You have been assigned a task: {instance.name}",
    )

    create_todo_once(
        title=f"Complete assigned task: {instance.name}",
        description=instance.description or "Please complete this assigned task.",
        owner=actor or instance.assigned_to,
        assigned_to=instance.assigned_to,
        priority=TodoPriority.HIGH,
        due_date=instance.due_date,
        project=instance.project,
        task=instance,
    )


@receiver(pre_save, sender=Deliverable)
def cache_old_deliverable_assignee(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_assigned_to_id = None
        return

    old = sender.objects.filter(pk=instance.pk).only("assigned_to").first()
    instance._old_assigned_to_id = old.assigned_to_id if old else None


@receiver(post_save, sender=Deliverable)
def notify_and_todo_deliverable_assigned(sender, instance, created, **kwargs):
    if not instance.assigned_to_id:
        return

    old_assigned_to_id = getattr(instance, "_old_assigned_to_id", None)

    if not created and old_assigned_to_id == instance.assigned_to_id:
        return

    actor = getattr(instance.project, "manager", None) or getattr(instance, "owner", None)

    notify_user(
        recipient=instance.assigned_to,
        actor=actor,
        notif_type=Notification.Type.DELIVERABLE_ASSIGNED,
        target=instance,
        message=f"You have been assigned a deliverable: {instance.name}",
    )

    create_todo_once(
        title=f"Complete assigned deliverable: {instance.name}",
        description=instance.description or "Please complete this assigned deliverable.",
        owner=actor or instance.assigned_to,
        assigned_to=instance.assigned_to,
        priority=TodoPriority.HIGH,
        due_date=instance.due_date,
        project=instance.project,
        deliverable=instance,
    )