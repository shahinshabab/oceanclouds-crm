# projects/forms.py

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Q

from common.roles import (
    ROLE_ADMIN,
    ROLE_PROJECT_MANAGER,
    ROLE_EMPLOYEE,
    user_has_role,
)

from .models import (
    Project,
    Task,
    Deliverable,
    ProjectStatus,
    TaskStatus,
    DeliverableStatus,
)

User = get_user_model()


class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for _, field in self.fields.items():
            widget = field.widget
            existing = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing + " form-check-input").strip()
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing + " form-select").strip()
            else:
                widget.attrs["class"] = (existing + " form-control").strip()


class DateInput(forms.DateInput):
    input_type = "date"


def users_in_roles(*role_names):
    return (
        User.objects.filter(is_active=True, groups__name__in=role_names)
        .distinct()
        .order_by("first_name", "last_name", "username")
    )


class ProjectForm(BootstrapModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "client",
            "deal",
            "event",
            "project_directory",
            "description",
            "manager",
            "start_date",
            "due_date",
            "status",
            "priority",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "start_date": DateInput(),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["client"].required = False
        self.fields["deal"].required = False
        self.fields["event"].required = False
        self.fields["project_directory"].required = False
        self.fields["manager"].required = False

        self.fields["manager"].queryset = users_in_roles(ROLE_PROJECT_MANAGER)

        if self.user and user_has_role(self.user, ROLE_PROJECT_MANAGER):
            self.fields["manager"].initial = self.user


class TaskForm(BootstrapModelForm):
    class Meta:
        model = Task
        fields = [
            "project",
            "name",
            "department",
            "category",
            "directory",
            "count",
            "description",
            "assigned_to",
            "status",
            "priority",
            "due_date",
            "estimated_minutes",
            "sort_order",
        ]
        widgets = {
            "directory": forms.TextInput(attrs={"placeholder": "e.g. Wedding/RAW/Photos"}),
            "count": forms.TextInput(attrs={"placeholder": "e.g. 1500 RAW photos"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": DateInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        qs = Project.objects.all().order_by("-created_at")

        if self.user and user_has_role(self.user, ROLE_PROJECT_MANAGER):
            qs = qs.filter(manager=self.user)

        self.fields["project"].queryset = qs

        if project:
            self.fields["project"].initial = project
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)

        self.fields["assigned_to"].queryset = users_in_roles(ROLE_EMPLOYEE)

    def clean_status(self):
        status = self.cleaned_data.get("status")

        if status == TaskStatus.IN_PROGRESS:
            assigned_to = self.cleaned_data.get("assigned_to")
            if not assigned_to:
                raise forms.ValidationError("Assign an employee before moving task to In Progress.")

        return status


class TaskStatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status"]

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status not in dict(TaskStatus.choices):
            raise forms.ValidationError("Invalid task status.")
        return status


class DeliverableForm(BootstrapModelForm):
    class Meta:
        model = Deliverable
        fields = [
            "project",
            "name",
            "category",
            "type",
            "department",
            "directory",
            "description",
            "assigned_to",
            "status",
            "tasks",
            "preview_link",
            "file_link",
            "file",
            "version",
            "revision_count",
            "delivery_medium",
            "quantity",
            "handed_over_to",
            "due_date",
        ]
        widgets = {
            "directory": forms.TextInput(attrs={"placeholder": "Final output folder/path"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_date": DateInput(),
            "tasks": forms.SelectMultiple(attrs={"size": 8}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        project = kwargs.pop("project", None)
        super().__init__(*args, **kwargs)

        project_qs = Project.objects.all().order_by("-created_at")

        if self.user and user_has_role(self.user, ROLE_PROJECT_MANAGER):
            project_qs = project_qs.filter(manager=self.user)

        self.fields["project"].queryset = project_qs

        if project:
            self.fields["project"].initial = project
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)
            self.fields["tasks"].queryset = project.tasks.all().order_by("sort_order", "name")
        elif self.instance and self.instance.pk:
            self.fields["tasks"].queryset = self.instance.project.tasks.all().order_by("sort_order", "name")
        else:
            self.fields["tasks"].queryset = Task.objects.none()

        self.fields["assigned_to"].queryset = users_in_roles(
            ROLE_PROJECT_MANAGER,
            ROLE_EMPLOYEE,
        )

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        tasks = cleaned.get("tasks")

        if status in [
            DeliverableStatus.IN_PROGRESS,
            DeliverableStatus.INTERNAL_REVIEW,
            DeliverableStatus.CLIENT_REVIEW,
            DeliverableStatus.READY_TO_DELIVER,
            DeliverableStatus.DELIVERED,
        ]:
            if tasks and tasks.exists():
                if tasks.exclude(status=TaskStatus.COMPLETED).exists():
                    raise forms.ValidationError(
                        "All linked tasks must be completed before moving this deliverable forward."
                    )

        return cleaned