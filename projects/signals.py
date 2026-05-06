# projects/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from common.models import Notification
from common.notifications import notify_user
from projects.models import Project, Task, Deliverable, ProjectStatus


@receiver(pre_save, sender=Project)
def cache_old_project_values(sender, instance, **kwargs):
    """
    Store old project manager and status before saving.
    """
    if not instance.pk:
        instance._old_manager_id = None
        instance._old_status = None
        return

    old = sender.objects.filter(pk=instance.pk).only("manager", "status").first()

    instance._old_manager_id = old.manager_id if old else None
    instance._old_status = old.status if old else None


@receiver(post_save, sender=Project)
def notify_project_changes(sender, instance, created, **kwargs):
    """
    Handles:
    - project assigned
    - project manager changed
    - project completed -> review pending notification
    """

    old_manager_id = getattr(instance, "_old_manager_id", None)
    old_status = getattr(instance, "_old_status", None)

    # Project assigned on create or manager changed
    if instance.manager_id and (created or old_manager_id != instance.manager_id):
        notify_user(
            recipient=instance.manager,
            actor=getattr(instance, "owner", None),
            notif_type=Notification.Type.PROJECT_ASSIGNED,
            target=instance,
            message=f"You have been assigned to project: {instance.name}",
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


def _resolve_project_review_recipient(project):
    """
    Decide who should collect the client review after project completion.

    Priority:
    1. deal.owner
    2. lead.owner through deal
    3. client.owner
    4. project.manager
    """

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
    """
    Store old assigned_to before saving.
    """
    if not instance.pk:
        instance._old_assigned_to_id = None
        return

    old = sender.objects.filter(pk=instance.pk).only("assigned_to").first()
    instance._old_assigned_to_id = old.assigned_to_id if old else None


@receiver(post_save, sender=Task)
def notify_task_assigned(sender, instance, created, **kwargs):
    """
    Notify employee when task is assigned or reassigned.
    """

    if not instance.assigned_to_id:
        return

    old_assigned_to_id = getattr(instance, "_old_assigned_to_id", None)

    if not created and old_assigned_to_id == instance.assigned_to_id:
        return

    actor = (
        getattr(instance, "created_by", None)
        or getattr(instance.project, "manager", None)
    )

    notify_user(
        recipient=instance.assigned_to,
        actor=actor,
        notif_type=Notification.Type.TASK_ASSIGNED,
        target=instance,
        message=f"You have been assigned a task: {instance.name}",
    )


@receiver(pre_save, sender=Deliverable)
def cache_old_deliverable_assignee(sender, instance, **kwargs):
    """
    Store old deliverable assignee before saving.
    """
    if not instance.pk:
        instance._old_assigned_to_id = None
        return

    old = sender.objects.filter(pk=instance.pk).only("assigned_to").first()
    instance._old_assigned_to_id = old.assigned_to_id if old else None


@receiver(post_save, sender=Deliverable)
def notify_deliverable_assigned(sender, instance, created, **kwargs):
    """
    Notify user when deliverable is assigned or reassigned.
    """

    if not instance.assigned_to_id:
        return

    old_assigned_to_id = getattr(instance, "_old_assigned_to_id", None)

    if not created and old_assigned_to_id == instance.assigned_to_id:
        return

    notify_user(
        recipient=instance.assigned_to,
        actor=getattr(instance.project, "manager", None),
        notif_type=Notification.Type.DELIVERABLE_ASSIGNED,
        target=instance,
        message=f"You have been assigned a deliverable: {instance.name}",
    )