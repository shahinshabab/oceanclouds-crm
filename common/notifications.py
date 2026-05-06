# common/notifications.py

from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, transaction


from common.models import Notification

def _target_identity(target):
    """
    Returns content_type and object_id for GenericForeignKey.
    """
    if target is None:
        return None, None

    return ContentType.objects.get_for_model(
        target,
        for_concrete_model=False,
    ), target.pk


def build_dedupe_key(notif_type, target=None, extra_key=""):
    """
    Example output:
    project_assigned:projects.project:12
    task_due:projects.task:44:2026-05-07
    """
    if target is not None:
        app_label = target._meta.app_label
        model_name = target._meta.model_name
        object_id = target.pk
        base = f"{notif_type}:{app_label}.{model_name}:{object_id}"
    else:
        base = f"{notif_type}:global"

    if extra_key:
        base = f"{base}:{extra_key}"

    return base[:180]


def notify_user(
    *,
    recipient,
    notif_type,
    target=None,
    message="",
    actor=None,
    dedupe_key=None,
    extra_key="",
    allow_duplicate=False,
):
    if not recipient:
        return None

    if actor and actor.pk == recipient.pk:
        return None

    content_type, object_id = _target_identity(target)

    if not message:
        message = dict(Notification.Type.choices).get(notif_type, notif_type)

    if allow_duplicate:
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            notif_type=notif_type,
            content_type=content_type,
            object_id=object_id,
            message=message,
            dedupe_key=None,
        )

    dedupe_key = dedupe_key or build_dedupe_key(
        notif_type=notif_type,
        target=target,
        extra_key=extra_key,
    )

    notification, created = Notification.objects.get_or_create(
        recipient=recipient,
        dedupe_key=dedupe_key,
        defaults={
            "actor": actor,
            "notif_type": notif_type,
            "content_type": content_type,
            "object_id": object_id,
            "message": message,
        },
    )

    return notification


def notify_many(
    *,
    recipients,
    notif_type,
    target=None,
    message="",
    actor=None,
    extra_key="",
):
    created = []

    for recipient in recipients:
        notif = notify_user(
            recipient=recipient,
            actor=actor,
            notif_type=notif_type,
            target=target,
            message=message,
            extra_key=extra_key,
        )
        if notif:
            created.append(notif)

    return created