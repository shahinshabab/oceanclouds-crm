# Generated manually to create one checklist per event

from django.db import migrations


def forwards(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    EventChecklist = apps.get_model("events", "EventChecklist")
    ChecklistItem = apps.get_model("events", "ChecklistItem")

    # 1. Create one checklist for every existing event
    for event in Event.objects.all():
        EventChecklist.objects.get_or_create(
            event_id=event.id,
            defaults={
                "title": f"Checklist for {event.name}",
                "owner_id": event.owner_id,
                "notes": "",
            },
        )

    # 2. Handle old checklist items that have no checklist.
    # Because the old event field was already removed in migration 0010,
    # we cannot safely know which event they belonged to.
    #
    # If this is development data, deleting orphan checklist items is cleanest.
    ChecklistItem.objects.filter(checklist_id__isnull=True).delete()


def backwards(apps, schema_editor):
    # No safe reverse because the old ChecklistItem.event field no longer exists.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0010_eventchecklist_alter_checklistitem_options_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]