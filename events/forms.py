# events/forms.py
from django import forms

from .models import Venue, Event, EventPerson, ChecklistItem, EventVendor


class BootstrapModelForm(forms.ModelForm):
    """
    Base form to automatically add Bootstrap classes to widgets.
    - Text / number / email / URL / textarea / date / time => form-control
    - Select / ModelChoiceField => form-select
    - Checkbox => form-check-input
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            # Keep any existing classes
            existing_classes = widget.attrs.get("class", "")

            # Checkbox
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing_classes + " form-check-input").strip()

            # Selects (ChoiceField, ModelChoiceField, etc.)
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing_classes + " form-select").strip()

            # Everything else → form-control
            else:
                widget.attrs["class"] = (existing_classes + " form-control").strip()


class DateInput(forms.DateInput):
    input_type = "date"


class TimeInput(forms.TimeInput):
    input_type = "time"


class VenueForm(BootstrapModelForm):
    class Meta:
        model = Venue
        fields = [
            "name",
            "venue_type",
            "contact_name",
            "phone",
            "email",
            "address_line1",
            "address_line2",
            "city",
            "district",
            "state",
            "country",
            "capacity",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class EventForm(BootstrapModelForm):
    class Meta:
        model = Event
        fields = [
            "client",
            "primary_contact",
            "name",
            "event_type",
            "status",
            "date",
            "start_time",
            "end_time",
            "venue",
            "expected_guests",
            "notes",
        ]
        widgets = {
            "date": DateInput(),
            "start_time": TimeInput(),
            "end_time": TimeInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class EventPersonForm(BootstrapModelForm):
    """
    Form for bride / groom / key people.
    """
    class Meta:
        model = EventPerson
        fields = [
            "event",
            "role",
            "full_name",
            "email",
            "phone",
            "whatsapp",
            "allow_marketing",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class ChecklistItemForm(BootstrapModelForm):
    class Meta:
        model = ChecklistItem
        fields = [
            "event",
            "title",
            "category",
            "is_done",
            "due_date",
            "assigned_to",
            "vendor",
            "notes",
        ]
        widgets = {
            "due_date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class EventVendorForm(BootstrapModelForm):
    class Meta:
        model = EventVendor
        fields = [
            "event",
            "vendor",
            "service",
            "role",
            "cost_estimate",
            "cost_actual",
            "is_confirmed",
            "notes",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
