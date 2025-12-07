# projects/models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.db.models import Q 

from common.models import TimeStamped, Owned


# -----------------------------
# Choice enums
# -----------------------------

class ProjectStatus(models.TextChoices):
    PLANNED = "planned", "Planned"
    ACTIVE = "active", "Active"
    ON_HOLD = "on_hold", "On Hold"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class TaskStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    BLOCKED = "blocked", "Blocked"


class Priority(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class DeliverableStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    DELIVERED = "delivered", "Delivered"
    CANCELLED = "cancelled", "Cancelled"


class FileType(models.TextChoices):
    IMAGE = "image", "Image"
    VIDEO = "video", "Video"
    MIXED = "mixed", "Image + Video"
    OTHER = "other", "Other"


class DeliverableType(models.TextChoices):
    DIGITAL = "digital", "Digital"
    PHYSICAL = "physical", "Physical item"
    MIXED = "mixed", "Digital + Physical"


# -----------------------------
# Project
# -----------------------------

class Project(TimeStamped, Owned):
    """
    Internal coordination unit for a wedding / deal.
    Typically created by ADMIN and assigned to one responsible MANAGER.
    """

    name = models.CharField(max_length=255)

    client = models.ForeignKey(
        "crm.Client",
        on_delete=models.CASCADE,
        related_name="projects",
    )

    deal = models.ForeignKey(
        "sales.Deal",
        on_delete=models.SET_NULL,
        related_name="projects",
        null=True,
        blank=True,
        help_text="Linked sales deal (optional).",
    )

    description = models.TextField(
        blank=True,
        help_text="Internal notes or summary of what this project covers.",
    )

    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="managed_projects",
        null=True,
        blank=True,
        help_text="Project owner on the operations side (usually a Manager).",
    )

    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="Planned start date for this project.",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target completion date for this project.",
    )

    status = models.CharField(
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PLANNED,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )

    event = models.ForeignKey(
        "events.Event",
        on_delete=models.SET_NULL,
        related_name="projects",
        null=True,
        blank=True,
        help_text="Event this project is handling (wedding, reception, etc.).",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.client})"

    # ---------- URLs ---------- #

    def get_absolute_url(self):
        return reverse("projects:project_detail", args=[self.pk])

    # ---------- Progress / completion helpers ---------- #

    @property
    def progress_percent(self) -> int:
        """
        Overall progress based on:
        - Completed tasks
        - Delivered deliverables
        """
        task_total = self.tasks.count()
        deliv_total = self.deliverables.count()
        total_items = task_total + deliv_total

        if not total_items:
            return 0

        completed_tasks = self.tasks.filter(status=TaskStatus.COMPLETED).count()
        delivered_items = self.deliverables.filter(
            status=DeliverableStatus.DELIVERED
        ).count()

        done = completed_tasks + delivered_items
        return int((done / total_items) * 100)

    @property
    def progress_bar_width(self) -> int:
        """
        Returns a minimum of 5% so that '0%' progress
        still shows a visible bar in the UI.
        """
        pct = int(self.progress_percent or 0)
        return max(pct, 5)

    @property
    def tasks_completed(self) -> bool:
        """
        True if there is at least one task and
        all tasks are marked COMPLETED.
        """
        if not self.tasks.exists():
            return False
        return not self.tasks.exclude(status=TaskStatus.COMPLETED).exists()

    @property
    def deliverables_delivered(self) -> bool:
        """
        True if there is at least one deliverable and
        all are marked DELIVERED.
        """
        if not self.deliverables.exists():
            return False
        return not self.deliverables.exclude(
            status=DeliverableStatus.DELIVERED
        ).exists()

    @property
    def can_be_completed(self) -> bool:
        """
        Project can be marked COMPLETED only if:
        - All tasks are completed (if any), AND
        - All deliverables are delivered (if any).
        """
        return self.tasks_completed and self.deliverables_delivered

    @property
    def is_overdue(self) -> bool:
        """
        Project is overdue if there is a due_date,
        it's not completed/cancelled, and today > due_date.
        """
        if not self.due_date:
            return False
        if self.status in {ProjectStatus.COMPLETED, ProjectStatus.CANCELLED}:
            return False
        return timezone.localdate() > self.due_date

    def mark_completed(self):
        """
        Safe helper to mark the project as COMPLETED,
        enforcing tasks + deliverables completion.
        """
        if self.status == ProjectStatus.COMPLETED:
            return  # idempotent

        if not self.can_be_completed:
            raise ValidationError(
                "Cannot complete project until all tasks and deliverables are done."
            )

        self.status = ProjectStatus.COMPLETED
        self.save(update_fields=["status"])


# -----------------------------
# Task
# -----------------------------

class Task(TimeStamped, Owned):
    """
    Internal work item under a Project.
    Manager assigns tasks to employees in their team.
    One task typically refers to editing / culling a specific folder/batch.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    name = models.CharField(
        max_length=255,
        help_text="Short name for the task (e.g., 'Culling – Haldi Photos').",
    )

    directory = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Folder path or directory for source files (optional).",
    )

    type = models.CharField(
        max_length=20,
        choices=FileType.choices,
        default=FileType.IMAGE,
        help_text="Main file type handled in this task.",
    )

    count = models.CharField(
        max_length=255,
        blank=True,
        help_text="File count or brief notes (e.g., '1500 RAW photos', '3 reels').",
    )

    description = models.TextField(
        blank=True,
        help_text="Detailed instructions or notes for this task.",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
        help_text="Employee responsible for this task.",
    )

    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.PENDING,
        db_index=True,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Target date for completing this task.",
    )
    first_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this task was first moved from Pending to In Progress.",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the task was marked completed.",
    )
    
    class Meta:
        ordering = ["status", "priority", "due_date", "created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project})"

    def get_absolute_url(self):
        return reverse("projects:task_detail", args=[self.pk])

    @property
    def is_completed(self) -> bool:
        return self.status == TaskStatus.COMPLETED

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        if self.is_completed:
            return False
        return timezone.localdate() > self.due_date

    def mark_completed(self):
        """
        Mark the task as COMPLETED and set completed_at timestamp.
        """
        if self.is_completed:
            return  # idempotent

        self.status = TaskStatus.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])


# -----------------------------
# Deliverable
# -----------------------------

class Deliverable(TimeStamped, Owned):
    """
    Final output for the client – edited photos, videos, albums, etc.
    Assigned to a Manager or Employee who is responsible to complete and hand over.
    """

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="deliverables",
    )

    name = models.CharField(
        max_length=255,
        help_text="Name of deliverable (e.g., 'Edited Wedding Photos', 'Highlight Film').",
    )

    directory = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Folder path or directory for source files (optional).",
    )

    description = models.TextField(
        blank=True,
        help_text="Internal description or notes for this deliverable.",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliverables_assigned",
        help_text="Manager or employee responsible for this deliverable.",
    )

    type = models.CharField(
        max_length=20,
        choices=DeliverableType.choices,
        default=DeliverableType.DIGITAL,
        help_text="Whether this deliverable is digital, physical, or mixed.",
    )

    status = models.CharField(
        max_length=20,
        choices=DeliverableStatus.choices,
        default=DeliverableStatus.PENDING,
        db_index=True,
    )

    # DIGITAL STORAGE
    file_link = models.URLField(
        blank=True,
        help_text="Google Drive / S3 / file URL where the deliverable is stored.",
    )

    file = models.FileField(
        upload_to="deliverables/",
        blank=True,
        null=True,
        help_text="Optional file stored in your own storage.",
    )

    # Link to tasks that produced this deliverable
    tasks = models.ManyToManyField(
        "Task",
        related_name="deliverables",
        blank=True,
        help_text="Tasks that produced this deliverable.",
    )

    # PHYSICAL HANDOVER
    delivery_medium = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., Pendrive, Printed album, Photo book, Framed print.",
    )
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of physical items (if applicable).",
    )
    handed_over_to = models.CharField(
        max_length=255,
        blank=True,
        help_text="Name of person who received it (bride/groom/family).",
    )

    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Target date for delivering this item.",
    )
    first_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this deliverable was first moved from Pending to In Progress.",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when this deliverable was marked delivered.",
    )

    class Meta:
        ordering = ["status", "due_date", "created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.project})"

    def get_absolute_url(self):
        return reverse("projects:deliverable_detail", args=[self.pk])

    @property
    def is_delivered(self) -> bool:
        return self.status == DeliverableStatus.DELIVERED

    @property
    def is_overdue(self) -> bool:
        if not self.due_date:
            return False
        if self.is_delivered:
            return False
        return timezone.localdate() > self.due_date

    def can_be_marked_delivered(self) -> bool:
        """
        A deliverable can be marked as DELIVERED only if:
        - It has no related tasks, OR
        - All related tasks are COMPLETED.
        """
        qs = self.tasks.all()
        if not qs.exists():
            return True  # no tasks linked → allow
        return not qs.exclude(status=TaskStatus.COMPLETED).exists()

    def mark_delivered(self):
        """
        Safe helper that enforces the task-completion rule.
        """
        if self.is_delivered:
            return  # idempotent

        if not self.can_be_marked_delivered():
            raise ValidationError(
                "All related tasks must be completed before marking this deliverable as delivered."
            )

        self.status = DeliverableStatus.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=["status", "delivered_at"])


class WorkLog(TimeStamped, Owned):
    """
    Tracks an 'active work' session for a Task or Deliverable.

    - A row is created when a user starts working (status -> IN_PROGRESS).
    - 'ended_at' is set when the item leaves IN_PROGRESS (to pending/blocked/completed).
    - Each user can have at most ONE active WorkLog (ended_at IS NULL)
      so they cannot have two tasks/deliverables in progress at the same time.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="work_logs",
    )

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="work_logs",
    )

    task = models.ForeignKey(
        "projects.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="work_logs",
        help_text="If this work session is for a Task.",
    )

    deliverable = models.ForeignKey(
        "projects.Deliverable",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="work_logs",
        help_text="If this work session is for a Deliverable.",
    )

    started_at = models.DateTimeField(
        db_index=True,
        help_text="When the user started working (status -> IN_PROGRESS).",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the user stopped working (status left IN_PROGRESS).",
    )

    class Meta:
        ordering = ["-started_at"]
        constraints = [
            # Either task OR deliverable must be set (not both, not neither)
            models.CheckConstraint(
                check=(
                    (Q(task__isnull=False) & Q(deliverable__isnull=True))
                    | (Q(task__isnull=True) & Q(deliverable__isnull=False))
                ),
                name="worklog_single_target",
            ),
            # At most ONE active (ended_at IS NULL) worklog per user
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(ended_at__isnull=True),
                name="worklog_one_active_per_user",
            ),
        ]

    def __str__(self):
        target = self.task or self.deliverable
        return f"WorkLog({self.user} on {target} from {self.started_at} to {self.ended_at or 'ACTIVE'})"

    @property
    def duration_seconds(self) -> int:
        """
        Duration in seconds for this work session.
        If still active, uses current time.
        """
        end = self.ended_at or timezone.now()
        return int((end - self.started_at).total_seconds())