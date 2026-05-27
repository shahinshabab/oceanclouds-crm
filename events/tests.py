from django.utils import timezone

from common.test_helpers import AuthenticatedViewTestMixin
from services.models import InventoryItem, Service, Vendor

from .forms import EventForm
from .models import ChecklistItem, Event, EventChecklist, Venue


class EventsTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "events:event_calendar",
        "events:venue_list",
        "events:event_list",
        "events:checklist_list",
    ]

    def test_venue_and_event_strings(self):
        venue = Venue.objects.create(name="Ocean Hall")
        event = Event.objects.create(
            name="Wedding",
            date=timezone.localdate(),
            venue=venue,
        )

        self.assertEqual(str(venue), "Ocean Hall")
        self.assertIn("Wedding", str(event))

    def test_event_checklist_is_created_and_counts_items(self):
        event = Event.objects.create(name="Reception", date=timezone.localdate())
        checklist = event.checklist
        ChecklistItem.objects.create(checklist=checklist, title="Call client")
        ChecklistItem.objects.create(checklist=checklist, title="Book crew", is_done=True)

        self.assertEqual(event.checklist_total, 2)
        self.assertEqual(event.checklist_done_count, 1)
        self.assertEqual(event.checklist_pending_count, 1)

    def test_sync_auto_checklist_adds_related_items_once(self):
        venue = Venue.objects.create(name="Beach Venue")
        service = Service.objects.create(name="Photography")
        vendor = Vendor.objects.create(name="Main Shooter")
        inventory = InventoryItem.objects.create(
            name="Camera",
            quantity_total=2,
            quantity_available=2,
        )
        event = Event.objects.create(
            name="Wedding",
            date=timezone.localdate(),
            venue=venue,
        )
        event.services.add(service)
        event.vendors.add(vendor)
        event.inventory_items.add(inventory)

        event.sync_auto_checklist()
        first_count = event.checklist.items.count()
        event.sync_auto_checklist()

        self.assertEqual(event.checklist.items.count(), first_count)
        self.assertGreaterEqual(first_count, 4)

    def test_checklist_item_string_and_event_property(self):
        event = Event.objects.create(name="Haldi", date=timezone.localdate())
        checklist = EventChecklist.objects.create(event=event, title="Haldi Checklist")
        item = ChecklistItem.objects.create(checklist=checklist, title="Decor")

        self.assertEqual(item.event, event)
        self.assertIn("Decor", str(item))

    def test_event_form_rejects_end_time_before_start_time(self):
        form = EventForm(
            data={
                "project": "",
                "client": "",
                "primary_contact": "",
                "name": "Wedding",
                "event_type": "wedding",
                "status": "planned",
                "date": timezone.localdate(),
                "start_time": "12:00",
                "end_time": "11:00",
                "venue": "",
                "services": [],
                "packages": [],
                "vendors": [],
                "inventory_items": [],
                "notes": "",
                "internal_notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)
