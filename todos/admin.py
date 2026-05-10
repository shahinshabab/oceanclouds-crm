# todos/admin.py

from django.contrib import admin

from todos.models import Todo


@admin.register(Todo)
class TodoAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "assigned_to",
        "status",
        "priority",
        "due_date",
        "is_overdue",
        "owner",
        "created_at",
    ]

    list_filter = [
        "status",
        "priority",
        "due_date",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "assigned_to__username",
        "assigned_to__first_name",
        "assigned_to__last_name",
        "owner__username",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
        "completed_at",
    ]

    autocomplete_fields = [
        "assigned_to",
        "project",
        "task",
        "deliverable",
        "client",
        "lead",
        "deal",
        "proposal",
        "contract",
        "invoice",
    ]

    date_hierarchy = "created_at"