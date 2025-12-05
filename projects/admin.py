# projects/admin.py

from django.contrib import admin

from .models import Project, Task, Deliverable


# ---------- Inlines ---------- #

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ("name", "assigned_to", "status", "priority", "due_date")
    show_change_link = True
    raw_id_fields = ("assigned_to",)


class DeliverableInline(admin.TabularInline):
    model = Deliverable
    extra = 0
    fields = (
        "name",
        "type",
        "status",
        "due_date",
        "delivered_at",
    )
    show_change_link = True
    raw_id_fields = ("assigned_to",)


# ---------- Project Admin ---------- #

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "client",
        "deal",
        "event",
        "manager",
        "status",
        "priority",
        "start_date",
        "due_date",
        "progress_percent",
        "is_overdue",
    )
    list_filter = (
        "status",
        "priority",
        "manager",
        "start_date",
        "due_date",
    )
    search_fields = (
        "name",
        "client__name",
        "deal__name",
        "event__name",
    )
    raw_id_fields = ("client", "deal", "event", "manager", "owner")
    inlines = [TaskInline, DeliverableInline]


# ---------- Task Admin ---------- #

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "assigned_to",
        "type",
        "status",
        "priority",
        "due_date",
        "is_overdue",
        "completed_at",
    )
    list_filter = (
        "status",
        "priority",
        "type",
        "assigned_to",
        "due_date",
    )
    search_fields = (
        "name",
        "directory",
        "project__name",
        "project__client__name",
    )
    raw_id_fields = ("project", "assigned_to", "owner")


# ---------- Deliverable Admin ---------- #

@admin.register(Deliverable)
class DeliverableAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "project",
        "type",
        "status",
        "due_date",
        "is_overdue",
        "delivered_at",
        "file_link",
    )
    list_filter = (
        "type",
        "status",
        "due_date",
        "delivered_at",
    )
    search_fields = (
        "name",
        "directory",
        "project__name",
        "project__client__name",
        "delivery_medium",
        "handed_over_to",
    )
    raw_id_fields = ("project", "assigned_to", "owner")
    filter_horizontal = ("tasks",)
