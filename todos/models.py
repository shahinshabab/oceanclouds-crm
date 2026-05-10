# todos/models.py

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from common.models import TimeStamped, Owned


class TodoStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TodoPriority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


class Todo(TimeStamped, Owned):
    """
    General to-do item.

    Can be used for:
    - personal tasks
    - CRM follow-ups
    - project follow-ups
    - client follow-ups
    - sales follow-ups
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_todos",
    )

    status = models.CharField(
        max_length=30,
        choices=TodoStatus.choices,
        default=TodoStatus.PENDING,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=TodoPriority.choices,
        default=TodoPriority.MEDIUM,
        db_index=True,
    )

    due_date = models.DateField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Optional links
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    task = models.ForeignKey(
        "projects.Task",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    deliverable = models.ForeignKey(
        "projects.Deliverable",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    client = models.ForeignKey(
        "crm.Client",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    lead = models.ForeignKey(
        "crm.Lead",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    deal = models.ForeignKey(
        "sales.Deal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    proposal = models.ForeignKey(
        "sales.Proposal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    contract = models.ForeignKey(
        "sales.Contract",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    invoice = models.ForeignKey(
        "sales.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )
    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )

    checklist_item = models.ForeignKey(
        "events.ChecklistItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todos",
    )
    class Meta:
        ordering = ["status", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["client", "status"]),
            models.Index(fields=["deal", "status"]),
            models.Index(fields=["event", "status"]),
            models.Index(fields=["checklist_item", "status"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("todos:todo_detail", args=[self.pk])

    @property
    def is_completed(self):
        return self.status == TodoStatus.COMPLETED

    @property
    def is_cancelled(self):
        return self.status == TodoStatus.CANCELLED

    @property
    def is_open(self):
        return self.status in [
            TodoStatus.PENDING,
            TodoStatus.IN_PROGRESS,
        ]

    @property
    def is_overdue(self):
        if not self.due_date:
            return False

        if self.status in [
            TodoStatus.COMPLETED,
            TodoStatus.CANCELLED,
        ]:
            return False

        return timezone.localdate() > self.due_date

    def mark_completed(self):
        if self.status == TodoStatus.COMPLETED:
            return

        self.status = TodoStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def reopen(self):
        self.status = TodoStatus.PENDING
        self.completed_at = None
        self.save(update_fields=["status", "completed_at"])

    def cancel(self):
        self.status = TodoStatus.CANCELLED
        self.save(update_fields=["status"])