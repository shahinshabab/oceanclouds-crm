# crm/signals.py

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from common.models import Notification
from common.notifications import notify_user
from crm.models import Inquiry


@receiver(pre_save, sender=Inquiry)
def cache_old_inquiry_handler(sender, instance, **kwargs):
    """
    Store old handled_by before saving.

    This lets us notify only when:
    - inquiry is newly created with handled_by
    - handled_by changed during update
    """
    if not instance.pk:
        instance._old_handled_by_id = None
        return

    old = sender.objects.filter(pk=instance.pk).only("handled_by").first()
    instance._old_handled_by_id = old.handled_by_id if old else None


@receiver(post_save, sender=Inquiry)
def notify_inquiry_assigned(sender, instance, created, **kwargs):
    """
    Notify CRM person when inquiry is assigned or reassigned.
    """

    if not instance.handled_by_id:
        return

    old_handled_by_id = getattr(instance, "_old_handled_by_id", None)

    if not created and old_handled_by_id == instance.handled_by_id:
        return

    notify_user(
        recipient=instance.handled_by,
        actor=getattr(instance, "owner", None),
        notif_type=Notification.Type.INQUIRY_ASSIGNED,
        target=instance,
        message=f"New inquiry assigned for follow-up: {instance}",
    )