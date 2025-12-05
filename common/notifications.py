# common/notifications.py

from django.contrib.contenttypes.models import ContentType

from common.models import Notification  # adjust if Notification is in another app


def create_notification(
    *,
    recipient,
    notif_type,
    target=None,
    message="",
    actor=None,
):
    """
    Helper to create a Notification.

    - recipient: User instance
    - notif_type: Notification.Type.<something>
    - target: model instance (Project, Task, Deliverable, etc.)
    - message: optional custom text
    - actor: User who triggered this (can be None)
    """
    content_type = None
    object_id = None

    if target is not None:
        content_type = ContentType.objects.get_for_model(target)
        object_id = target.pk

    if not message:
        # fallback to the verbose label for the type
        message = dict(Notification.Type.choices).get(notif_type, notif_type)

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notif_type=notif_type,
        content_type=content_type,
        object_id=object_id,
        message=message,
    )
