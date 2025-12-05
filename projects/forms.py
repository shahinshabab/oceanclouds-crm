# projects/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q

from .models import Project, Task, Deliverable, TaskStatus, DeliverableStatus

User = get_user_model()


# ---------- Bootstrap base + widgets ---------- #

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


class DateTimeInput(forms.DateTimeInput):
    input_type = "datetime-local"


# ---------- Project ---------- #

class ProjectForm(BootstrapModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "client",
            "deal",
            "event",
            "description",
            "manager",
            "start_date",
            "due_date",
            "status",
            "priority",
        ]
        widgets = {
            "start_date": DateInput(),
            "due_date": DateInput(),
            "description": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        # we still accept user, but don't strictly need it now
        kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # ---- Manager dropdown queryset: only "Manager" group ----
        try:
            manager_group = Group.objects.get(name__iexact="Manager")
            manager_qs = manager_group.user_set.filter(is_active=True)
        except Group.DoesNotExist:
            manager_qs = User.objects.none()

        # Exclude admins / superusers even if they were added to Manager group
        manager_qs = manager_qs.exclude(
            Q(is_superuser=True) | Q(groups__name__iexact="Admin")
        ).distinct()

        self.fields["manager"].queryset = manager_qs.order_by(
            "first_name",
            "last_name",
            "username",
        )
        self.fields["manager"].required = False


# ---------- Task ---------- #

class TaskForm(BootstrapModelForm):
    class Meta:
        model = Task
        fields = [
            "project",       # project selectable (or pre-filled from URL)
            "name",
            "directory",
            "type",
            "count",
            "description",
            "assigned_to",
            "status",
            "priority",
            "due_date",
        ]
        widgets = {
            "directory": forms.TextInput(
                attrs={"placeholder": "e.g. 'Rohan-Aisha/01_Haldi/RAW'"}
            ),
            "count": forms.TextInput(
                attrs={"placeholder": "e.g. '1500 RAW photos', '3 reels'"}
            ),
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        # accept BOTH user and project, but never pass them to super()
        user = kwargs.pop("user", None)
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        # ---- Project dropdown ----
        qs = Project.objects.order_by("name")

        # Manager: only their own projects
        if user and user.groups.filter(name__iexact="Manager").exists():
            qs = qs.filter(manager=user)

        self.fields["project"].queryset = qs

        # If a specific project was passed (from URL), preselect it
        if project is not None:
            self.fields["project"].initial = project

        # ---- Assigned_to dropdown (Employees) ----
        try:
            employee_group = Group.objects.get(name__iexact="Employee")
            self.fields["assigned_to"].queryset = employee_group.user_set.filter(
                is_active=True
            ).order_by("first_name", "last_name", "username")
        except Group.DoesNotExist:
            self.fields["assigned_to"].queryset = User.objects.none()


class TaskStatusForm(BootstrapModelForm):
    """
    Simplified form for employees to update only status.
    """

    class Meta:
        model = Task
        fields = ["status"]

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status not in [
            TaskStatus.PENDING,
            TaskStatus.IN_PROGRESS,
            TaskStatus.COMPLETED,
            TaskStatus.BLOCKED,
        ]:
            raise forms.ValidationError("Invalid status.")
        return status


# ---------- Deliverable ---------- #

class DeliverableForm(BootstrapModelForm):
    class Meta:
        model = Deliverable
        fields = [
            "project",
            "name",
            "directory",
            "description",
            "type",
            "status",
            "assigned_to",
            "tasks",
            "file_link",
            "file",
            "delivery_medium",
            "quantity",
            "handed_over_to",
            "due_date",
        ]
        widgets = {
            "directory": forms.TextInput(
                attrs={"placeholder": "Folder/path where final deliverables are stored"}
            ),
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        # ----- Project limiting ----- #
        qs = Project.objects.order_by("name")
        if user and user.groups.filter(name__iexact="Manager").exists():
            qs = qs.filter(manager=user)
        self.fields["project"].queryset = qs

        if project is not None:
            self.fields["project"].initial = project

        # ----- Limit tasks to selected project (if passed from view) ----- #
        if project is not None and "tasks" in self.fields:
            self.fields["tasks"].queryset = project.tasks.all()

        # ----- Assignee choices: all active Managers + Employees ----- #
        if "assigned_to" in self.fields:
            user_qs = User.objects.filter(
                is_active=True,
                groups__name__in=["Manager", "Employee"],
            ).distinct().order_by("first_name", "last_name", "username")
            self.fields["assigned_to"].queryset = user_qs

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        tasks = cleaned_data.get("tasks")

        # If using instance.tasks when tasks not on form:
        if tasks is None and self.instance.pk:
            tasks = self.instance.tasks.all()

        if status == DeliverableStatus.DELIVERED and tasks is not None:
            # If there are linked tasks, all must be COMPLETED
            if tasks.exists() and tasks.exclude(status=TaskStatus.COMPLETED).exists():
                raise forms.ValidationError(
                    "You can only mark this deliverable as Delivered when all linked tasks are Completed."
                )

        return cleaned_data
