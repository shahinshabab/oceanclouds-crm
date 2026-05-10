# todos/forms.py

from django import forms
from django.contrib.auth import get_user_model

from common.forms import BootstrapModelForm
from todos.models import Todo


User = get_user_model()


class DateInput(forms.DateInput):
    input_type = "date"


class TodoForm(BootstrapModelForm):
    class Meta:
        model = Todo
        fields = [
            "title",
            "description",
            "assigned_to",
            "status",
            "priority",
            "due_date",

            # Project links
            "project",
            "task",
            "deliverable",

            # CRM links
            "client",
            "lead",

            # Sales links
            "deal",
            "proposal",
            "contract",
            "invoice",

            # Event links
            "event",
            "checklist_item",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Main optional fields
        self.fields["assigned_to"].required = False
        self.fields["due_date"].required = False

        # Optional linked records
        optional_link_fields = [
            "project",
            "task",
            "deliverable",
            "client",
            "lead",
            "deal",
            "proposal",
            "contract",
            "invoice",
            "event",
            "checklist_item",
        ]

        for field_name in optional_link_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

        self.fields["assigned_to"].queryset = (
            User.objects
            .filter(is_active=True)
            .order_by("first_name", "last_name", "username")
        )

        self.fields["title"].widget.attrs.update({
            "placeholder": "e.g. Follow up client, Check delivery files, Call editor"
        })

        self.fields["description"].widget.attrs.update({
            "placeholder": "Optional notes about this to-do"
        })

        # Better empty labels for dropdowns
        dropdown_empty_labels = {
            "assigned_to": "Select user",
            "project": "Select project",
            "task": "Select task",
            "deliverable": "Select deliverable",
            "client": "Select client",
            "lead": "Select lead",
            "deal": "Select deal",
            "proposal": "Select proposal",
            "contract": "Select contract",
            "invoice": "Select invoice",
            "event": "Select event",
            "checklist_item": "Select checklist item",
        }

        for field_name, label in dropdown_empty_labels.items():
            if field_name in self.fields:
                self.fields[field_name].empty_label = label