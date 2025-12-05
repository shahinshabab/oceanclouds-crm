# projects/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from common.notifications import create_notification
from common.models import Notification  # adjust if Notification is elsewhere
from .models import Project, Task, Deliverable  # make sure these are correct imports


@receiver(post_save, sender=Project)
def notify_project_assigned(sender, instance, created, **kwargs):
    """
    Notify the project manager when a project is created.
    """
    if not created:
        return

    # Assuming Project has fields: name, manager, owner
    if instance.manager:
        create_notification(
            recipient=instance.manager,
            actor=getattr(instance, "owner", None),
            notif_type=Notification.Type.PROJECT_ASSIGNED,
            target=instance,
            message=f"You have been assigned to project: {instance}",
        )


@receiver(post_save, sender=Task)
def notify_task_assigned(sender, instance, created, **kwargs):
    """
    Notify assigned user when a task is created.
    Optional: also notify if assignment changed.
    """
    # Only on create for now
    if created and instance.assigned_to:
        create_notification(
            recipient=instance.assigned_to,
            actor=getattr(instance, "created_by", None),
            notif_type=Notification.Type.TASK_ASSIGNED,
            target=instance,
            message=f"New task assigned: {instance}",
        )

@receiver(post_save, sender=Deliverable)
def notify_deliverable_created(sender, instance, created, **kwargs):
    """
    Notify whoever should own deliverable (e.g. task.assigned_to or project.manager).
    """
    if not created:
        return

    recipient = None

    # Choose the logic that makes sense for your model structure:
    # example: Deliverable -> Task -> assigned_to
    if hasattr(instance, "task") and instance.task and instance.task.assigned_to:
        recipient = instance.task.assigned_to
    elif hasattr(instance, "project") and instance.project and instance.project.manager:
        recipient = instance.project.manager

    if not recipient:
        return

    create_notification(
        recipient=recipient,
        actor=getattr(instance, "created_by", None),
        notif_type=Notification.Type.DELIVERABLE_OVERDUE,  # or create a new type "deliverable_created" if you prefer
        target=instance,
        message=f"New deliverable created: {instance}",
    )
