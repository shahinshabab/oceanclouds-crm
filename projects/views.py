# projects/views.py

from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    TemplateView,
)

from django.contrib.auth.models import Group  # kept if you later need

from .forms import ProjectForm, TaskForm, TaskStatusForm, DeliverableForm
from .models import (
    Project,
    Task,
    Deliverable,
    TaskStatus,
    ProjectStatus,
    Priority,
    DeliverableStatus,
    DeliverableType,
    WorkLog
)

from common.notifications import create_notification
from common.models import Notification  # for Notification.Type
from decimal import Decimal
from django.db.models import Sum
from django.db.models.functions import Coalesce

# 🔹 central roles + mixins
from common.roles import (
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
    user_has_role,
)
from common.mixins import (
    AdminOnlyMixin,
    AdminManagerMixin,
    StaffAllMixin,
)

User = get_user_model()


# =====================================================================
#                         ROLE HELPERS (thin layer)
# =====================================================================


def is_admin(user) -> bool:
    return user_has_role(user, ROLE_ADMIN)


def is_manager(user) -> bool:
    return user_has_role(user, ROLE_MANAGER)


def is_employee(user) -> bool:
    return user_has_role(user, ROLE_EMPLOYEE)


# =====================================================================
#                          PROJECT VIEWS
# =====================================================================


class ProjectListView(AdminManagerMixin, ListView):
    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        qs = Project.objects.select_related(
            "client", "deal", "manager"
        ).prefetch_related("tasks", "deliverables")

        user = self.request.user

        if is_admin(user):
            pass  # all projects
        elif is_manager(user):
            qs = qs.filter(manager=user)
        elif is_employee(user):
            qs = qs.filter(tasks__assigned_to=user).distinct()
        else:
            qs = qs.none()

        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(client__name__icontains=q)
                | Q(deal__name__icontains=q)
            )

        # Optional extra filters (status / manager)
        status = self.request.GET.get("status")
        manager_id = self.request.GET.get("manager")

        if status:
            qs = qs.filter(status=status)
        if manager_id:
            qs = qs.filter(manager_id=manager_id)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["manager_filter"] = self.request.GET.get("manager", "")

        context["status_choices"] = ProjectStatus.choices

        # Managers list (for filter dropdown)
        context["manager_choices"] = User.objects.filter(
            groups__name__iexact="Manager"
        ).order_by("first_name", "last_name")

        return context


class ProjectDetailView(AdminManagerMixin, DetailView):
    """
    Original simple project detail view (tasks/deliverables etc).
    You can keep this for normal usage.
    """
    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        qs = (
            Project.objects.select_related("client", "deal", "manager")
            .prefetch_related("tasks__assigned_to", "deliverables__tasks")
        )

        user = self.request.user

        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(manager=user)
        elif is_employee(user):
            return qs.filter(tasks__assigned_to=user).distinct()
        return Project.objects.none()


class ProjectOverviewView(AdminManagerMixin, DetailView):
    model = Project
    template_name = "projects/project_overview.html"
    context_object_name = "project"

    def get_queryset(self):
        qs = (
            Project.objects.select_related("client", "deal", "manager")
            .prefetch_related(
                "tasks__assigned_to",
                "deliverables__assigned_to",
                # If you want, you can also prefetch deal invoices/payments later
            )
        )

        user = self.request.user
        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(manager=user)
        elif is_employee(user):
            return qs.filter(tasks__assigned_to=user).distinct()
        return Project.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project: Project = self.object
        deal = project.deal

        contracts_qs = []
        invoices_qs = []
        payments_qs = []

        invoice_total = None
        payments_total = None
        amount_due = None

        if deal:
            # Contracts (if Deal -> Contract FK exists)
            if hasattr(deal, "contracts"):
                contracts_qs = deal.contracts.all().annotate(
                    total_amount=Coalesce(Sum("items__line_total"), Decimal("0.00"))
                )

            # Invoices (Deal -> Invoice FK, related_name="invoices")
            if hasattr(deal, "invoices"):
                invoices_qs = deal.invoices.all().select_related("deal")

                # ✅ Payments usually linked to Invoice, not Deal
                # Try invoice.payments reverse relation
                # Build a payments queryset from invoices
                invoice_ids = invoices_qs.values_list("id", flat=True)

                # If Payment model has FK: invoice = ForeignKey(Invoice, related_name="payments", ...)
                # then invoices_qs[0].payments exists, but easiest:
                from sales.models import Payment  # adjust import if needed
                payments_qs = (
                    Payment.objects
                    .filter(invoice_id__in=invoice_ids)
                    .select_related("invoice")
                    .order_by("-date", "-created_at")
                )

                # ✅ Totals (safe Coalesce to avoid None)
                invoice_total = invoices_qs.aggregate(
                    total=Coalesce(Sum("total"), Decimal("0.00"))
                )["total"]

                payments_total = payments_qs.aggregate(
                    total=Coalesce(Sum("amount"), Decimal("0.00"))
                )["total"]

                amount_due = invoice_total - payments_total

        tasks_qs = project.tasks.select_related("assigned_to").order_by("due_date", "status")
        deliverables_qs = project.deliverables.select_related("assigned_to").order_by("due_date", "status")

        context.update(
            {
                "client": project.client,
                "deal": deal,
                "contracts": contracts_qs,
                "invoices": invoices_qs,
                "payments": payments_qs,

                # ✅ KPI card values used in template
                "invoice_total": invoice_total,
                "payments_total": payments_total,
                "amount_due": amount_due,

                "tasks": tasks_qs,
                "deliverables": deliverables_qs,
            }
        )
        return context



class ProjectCreateView(AdminOnlyMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        After creating the project, notify the assigned manager (if any).
        """
        response = super().form_valid(form)

        project = self.object
        manager = getattr(project, "manager", None)

        if manager:
            create_notification(
                recipient=manager,
                actor=self.request.user,
                notif_type=Notification.Type.PROJECT_ASSIGNED,
                target=project,
                message=f"You have been assigned to project: {project.name}",
            )

        return response

    def get_success_url(self):
        return reverse("projects:project_detail", args=[self.object.pk])


class ProjectUpdateView(AdminManagerMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"

    def get_queryset(self):
        qs = Project.objects.all()
        user = self.request.user
        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(manager=user)
        return Project.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        """
        If the manager changes, notify the new manager.
        """
        old_project = self.get_object()
        old_manager = old_project.manager

        response = super().form_valid(form)

        project = self.object
        new_manager = project.manager

        if new_manager and new_manager != old_manager:
            create_notification(
                recipient=new_manager,
                actor=self.request.user,
                notif_type=Notification.Type.PROJECT_ASSIGNED,
                target=project,
                message=f"You have been reassigned to project: {project.name}",
            )

        return response


# ---------------- PROJECT KANBAN ---------------- #


class ProjectKanbanView(AdminManagerMixin, TemplateView):
    """
    Kanban board for Projects.
    Columns = ProjectStatus
    Cards = projects visible to current user.
    """

    template_name = "projects/project_kanban.html"

    def get_queryset(self):
        qs = (
            Project.objects.select_related("client", "deal", "manager")
            .prefetch_related("tasks", "deliverables")
        )
        user = self.request.user

        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(manager=user)
        elif is_employee(user):
            return qs.filter(tasks__assigned_to=user).distinct()
        return Project.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        projects_by_status = {}
        for key, label in ProjectStatus.choices:
            projects_by_status[key] = qs.filter(status=key)
        context["projects_by_status"] = projects_by_status
        context["status_choices"] = ProjectStatus.choices
        return context


class ProjectStatusUpdateView(AdminManagerMixin, View):
    """
    AJAX endpoint to change project status via drag-and-drop in Kanban.
    URL example: /projects/<pk>/set-status/
    POST data: { "status": "active" }
    """

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        user = request.user

        # Manager can only update their own project's status
        if is_manager(user) and project.manager != user and not is_admin(user):
            return JsonResponse(
                {"success": False, "error": "Not allowed to modify this project."},
                status=403,
            )

        new_status = request.POST.get("status")
        valid_statuses = {choice[0] for choice in ProjectStatus.choices}
        if new_status not in valid_statuses:
            return JsonResponse(
                {"success": False, "error": "Invalid status."}, status=400
            )

        # If trying to mark completed, enforce can_be_completed
        if new_status == ProjectStatus.COMPLETED and hasattr(project, "can_be_completed"):
            if not project.can_be_completed:
                return JsonResponse(
                    {
                        "success": False,
                        "error": (
                            "All tasks and deliverables must be completed "
                            "before closing the project."
                        ),
                    },
                    status=400,
                )

        project.status = new_status
        project.save(update_fields=["status"])

        return JsonResponse({"success": True, "status": new_status})


# =====================================================================
#                          TASK VIEWS
# =====================================================================

class TaskListView(StaffAllMixin, ListView):
    """
    Shows tasks according to role:
    - Admin: all
    - Manager: tasks for projects where manager=user
    - Employee: tasks assigned_to=user

    Only tasks belonging to projects that are NOT completed.
    Ordered by due_date.
    """

    model = Task
    template_name = "projects/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        qs = Task.objects.select_related("project", "assigned_to", "project__client")
        user = self.request.user

        # 🔹 Only tasks for projects that are NOT completed
        qs = qs.exclude(project__status=ProjectStatus.COMPLETED)

        # ---- ROLE FILTERS ----
        if is_admin(user):
            pass
        elif is_manager(user):
            qs = qs.filter(project__manager=user)
        elif is_employee(user):
            qs = qs.filter(assigned_to=user)
        else:
            qs = Task.objects.none()

        # Search
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(project__name__icontains=q)
            )

        # Filters
        status = self.request.GET.get("status")
        priority = self.request.GET.get("priority")
        due_filter = self.request.GET.get("due")
        today = timezone.localdate()

        if status:
            qs = qs.filter(status=status)
        if priority:
            qs = qs.filter(priority=priority)

        # 🔹 Due-date filter: overdue / today / upcoming / no_due
        if due_filter == "overdue":
            qs = qs.filter(due_date__lt=today).exclude(status=TaskStatus.COMPLETED)
        elif due_filter == "today":
            qs = qs.filter(due_date=today)
        elif due_filter == "upcoming":
            qs = qs.filter(due_date__gt=today)
        elif due_filter == "no_due":
            qs = qs.filter(due_date__isnull=True)

        # Order by due_date (then status/priority)
        qs = qs.order_by("due_date", "status", "priority", "created_at")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["priority_filter"] = self.request.GET.get("priority", "")
        context["due_filter"] = self.request.GET.get("due", "")

        context["status_choices"] = TaskStatus.choices
        context["priority_choices"] = Priority.choices

        # For template: possible due filter options
        context["due_filter_options"] = [
            ("", "All"),
            ("overdue", "Overdue"),
            ("today", "Due Today"),
            ("upcoming", "Upcoming"),
            ("no_due", "No Due Date"),
        ]

        return context


class TaskCreateView(AdminManagerMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "projects/task_form.html"
    success_url = reverse_lazy("projects:task_list")

    def dispatch(self, request, *args, **kwargs):
        self.project = None
        project_pk = self.kwargs.get("project_pk")
        if project_pk:
            self.project = get_object_or_404(Project, pk=project_pk)
            user = request.user

            # Manager can create tasks only for their own projects; admin for all.
            if is_manager(user) and self.project.manager != user and not is_admin(user):
                messages.error(
                    request,
                    "You are not allowed to add tasks to this project.",
                )
                return redirect("projects:project_detail", pk=self.project.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if self.project is not None:
            kwargs["project"] = self.project
        return kwargs

    def form_valid(self, form):
        response = super().form_valid(form)

        task = self.object
        assignee = getattr(task, "assigned_to", None)

        if assignee:
            task_label = getattr(task, "name", None) or str(task)
            create_notification(
                recipient=assignee,
                actor=self.request.user,
                notif_type=Notification.Type.TASK_ASSIGNED,
                target=task,
                message=f"You have been assigned a task: {task_label}",
            )

        return response


class TaskUpdateView(AdminManagerMixin, UpdateView):
    """
    Only Admin + Manager can update tasks via this form.
    Employees CANNOT access this view.
    """
    model = Task
    template_name = "projects/task_form.html"
    form_class = TaskForm  # always full form

    def get_queryset(self):
        qs = Task.objects.select_related("project", "assigned_to", "project__manager")
        user = self.request.user

        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(project__manager=user)
        # AdminManagerMixin will already block others, but be explicit:
        return Task.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        task = form.save(commit=False)
        user = self.request.user
        old = Task.objects.get(pk=task.pk)
        new_status = form.cleaned_data["status"]

        # Start WorkLog
        if new_status == TaskStatus.IN_PROGRESS and old.status != TaskStatus.IN_PROGRESS:
            if WorkLog.objects.filter(user=user, ended_at__isnull=True).exists():
                messages.error(self.request, "You already have another item in progress.")
                return redirect("projects:task_detail", pk=task.pk)

            if task.first_started_at is None:
                task.first_started_at = timezone.now()

            WorkLog.objects.create(
                user=user,
                project=task.project,
                task=task,
                started_at=timezone.now()
            )

        # End WorkLog
        if old.status == TaskStatus.IN_PROGRESS and new_status != TaskStatus.IN_PROGRESS:
            WorkLog.objects.filter(
                user=user, task=task, ended_at__isnull=True
            ).update(ended_at=timezone.now())

        # Completed timestamp
        if new_status == TaskStatus.COMPLETED and task.completed_at is None:
            task.completed_at = timezone.now()

        task.save()
        form.save_m2m()
        messages.success(self.request, "Task updated successfully.")
        return redirect("projects:project_detail", pk=task.project.pk)



class TaskDetailView(StaffAllMixin, DetailView):
    """
    Visible to:
    - Admin: any task
    - Manager: tasks for projects they manage
    - Employee: ONLY tasks assigned to them
    """
    model = Task
    template_name = "projects/task_detail.html"
    context_object_name = "task"

    def get_queryset(self):
        qs = Task.objects.select_related(
            "project",
            "project__client",
            "project__manager",
            "assigned_to",
        ).prefetch_related("deliverables")

        user = self.request.user

        if is_admin(user):
            return qs
        elif is_manager(user):
            return qs.filter(project__manager=user)
        elif is_employee(user):
            return qs.filter(assigned_to=user)
        return Task.objects.none()


@login_required
def ajax_load_tasks(request):
    """
    Returns JSON list of tasks for a given project.
    Used by Deliverable form when project dropdown changes.
    """
    project_id = request.GET.get("project")
    qs = Task.objects.none()

    if project_id:
        qs = Task.objects.filter(project_id=project_id).order_by("name")

        # optional: extra permission filtering
        user = request.user
        if is_admin(user):
            pass
        elif is_manager(user):
            qs = qs.filter(project__manager=user)
        elif is_employee(user):
            qs = qs.filter(assigned_to=user)
        else:
            qs = Task.objects.none()

    data = [
        {"id": task.id, "name": task.name}
        for task in qs
    ]
    return JsonResponse(data, safe=False)


# ---------------- TASK KANBAN ---------------- #


class TaskKanbanView(StaffAllMixin, TemplateView):
    """
    Kanban board for Tasks.
    Shows tasks only for projects that are NOT completed.
    Columns = TaskStatus
    """

    template_name = "projects/task_kanban.html"

    def get_queryset(self):
        qs = Task.objects.select_related(
            "project", "assigned_to", "project__client", "project__manager"
        )
        user = self.request.user

        # 🔹 Only tasks for projects that are NOT completed
        qs = qs.exclude(project__status=ProjectStatus.COMPLETED)

        if is_admin(user):
            pass   # full access
        elif is_manager(user):
            qs = qs.filter(project__manager=user)
        elif is_employee(user):
            qs = qs.filter(assigned_to=user)
        else:
            qs = Task.objects.none()

        # Order by due_date so inside each column they’re roughly sorted
        qs = qs.order_by("due_date", "status", "priority", "created_at")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        tasks_by_status = {}
        for key, label in TaskStatus.choices:
            tasks_by_status[key] = qs.filter(status=key)
        context["tasks_by_status"] = tasks_by_status
        context["status_choices"] = TaskStatus.choices

        return context


class TaskStatusUpdateView(StaffAllMixin, View):

    def post(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        user = request.user
        new_status = request.POST.get("status")

        # Permission checks
        if is_employee(user) and task.assigned_to != user:
            return JsonResponse({"success": False, "error": "Not allowed."}, status=403)

        if is_manager(user) and task.project.manager != user and not is_admin(user):
            return JsonResponse({"success": False, "error": "Not allowed."}, status=403)

        valid = {c[0] for c in TaskStatus.choices}
        if new_status not in valid:
            return JsonResponse({"success": False, "error": "Invalid status"}, status=400)

        old_status = task.status

        # --------------------------------------------------------------------
        # 1) If moving INTO IN_PROGRESS → create WorkLog
        # --------------------------------------------------------------------
        if new_status == TaskStatus.IN_PROGRESS and old_status != TaskStatus.IN_PROGRESS:

            # Enforce "only 1 active worklog" rule
            if WorkLog.objects.filter(user=user, ended_at__isnull=True).exists():
                return JsonResponse({
                    "success": False,
                    "error": "You already have another task/deliverable in progress."
                }, status=400)

            # Set first_started_at only once
            if task.first_started_at is None:
                task.first_started_at = timezone.now()

            # Create WorkLog
            WorkLog.objects.create(
                user=user,
                project=task.project,
                task=task,
                started_at=timezone.now()
            )

        # --------------------------------------------------------------------
        # 2) If leaving IN_PROGRESS → close WorkLog
        # --------------------------------------------------------------------
        if old_status == TaskStatus.IN_PROGRESS and new_status != TaskStatus.IN_PROGRESS:
            WorkLog.objects.filter(
                user=user,
                task=task,
                ended_at__isnull=True
            ).update(ended_at=timezone.now())

        # --------------------------------------------------------------------
        # 3) Set completed timestamp if needed
        # --------------------------------------------------------------------
        if new_status == TaskStatus.COMPLETED and task.completed_at is None:
            task.completed_at = timezone.now()

        # --------------------------------------------------------------------
        # Save status
        # --------------------------------------------------------------------
        task.status = new_status
        task.save(update_fields=["status", "completed_at", "first_started_at"])

        return JsonResponse({"success": True, "status": new_status})



# =====================================================================
#                       DELIVERABLE VIEWS
# =====================================================================

class DeliverableListView(StaffAllMixin, ListView):
    """
    Visibility:
    - Admin/Manager: all deliverables for projects that are NOT completed
    - Employee: only deliverables assigned_to = request.user (also only for non-completed projects)

    Ordered by due_date.
    """
    model = Deliverable
    template_name = "projects/deliverable_list.html"
    context_object_name = "deliverables"
    paginate_by = 20

    def get_queryset(self):
        qs = Deliverable.objects.select_related(
            "project", "project__client", "assigned_to"
        )
        user = self.request.user

        # 🔹 Only deliverables for projects that are NOT completed
        qs = qs.exclude(project__status=ProjectStatus.COMPLETED)

        # ---- ROLE FILTERS ----
        if is_admin(user) or is_manager(user):
            # Admin + Manager: see everything (for non-completed projects)
            pass
        elif is_employee(user):
            # Employee: ONLY deliverables assigned to them
            qs = qs.filter(assigned_to=user)
        else:
            qs = Deliverable.objects.none()

        # ----- Search ----- #
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(project__name__icontains=q)
            )

        # ----- Filters: only status + type ----- #
        status = self.request.GET.get("status")
        d_type = self.request.GET.get("type")

        if status:
            qs = qs.filter(status=status)
        if d_type:
            qs = qs.filter(type=d_type)

        # Order by due_date
        qs = qs.order_by("due_date", "status", "created_at")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["q"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        context["type_filter"] = self.request.GET.get("type", "")

        context["status_choices"] = DeliverableStatus.choices
        context["type_choices"] = DeliverableType.choices

        # Optional: keep assignee choices if you ever want to add a filter later
        context["assignee_choices"] = (
            User.objects.filter(
                is_active=True,
                groups__name__in=["Manager", "Employee"],
            )
            .distinct()
            .order_by("first_name", "last_name", "username")
        )

        return context


class DeliverableCreateView(AdminManagerMixin, CreateView):
    """
    Only Admin & Manager can create.
    Admin & Manager can create deliverables for ANY project.
    """
    model = Deliverable
    form_class = DeliverableForm
    template_name = "projects/deliverable_form.html"

    def dispatch(self, request, *args, **kwargs):
        """
        Optional project_pk:
        - /projects/<project_pk>/deliverables/create/
        - /deliverables/create/
        """
        self.project = None
        project_pk = self.kwargs.get("project_pk")

        if project_pk:
            self.project = get_object_or_404(Project, pk=project_pk)

        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        if self.project:
            initial["project"] = self.project
        return initial

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        if self.project is not None:
            kwargs["project"] = self.project
        return kwargs

    def get_context_data(self, **kwargs):
        """
        So the template's `{% if project %}` branch works on create.
        """
        context = super().get_context_data(**kwargs)
        context["project"] = self.project
        return context

    def form_valid(self, form):
        deliverable = form.save(commit=False)
        user = self.request.user

        # If URL had project_pk, force that project
        if self.project is not None:
            deliverable.project = self.project

        if hasattr(deliverable, "owner"):
            deliverable.owner = user

        # If assigned_to not chosen, default to project's manager
        if (
            deliverable.assigned_to is None
            and deliverable.project
            and deliverable.project.manager
        ):
            deliverable.assigned_to = deliverable.project.manager

        deliverable.save()
        form.save_m2m()

        messages.success(self.request, "Deliverable created successfully.")
        return redirect("projects:deliverable_detail", pk=deliverable.pk)


class DeliverableUpdateView(AdminManagerMixin, UpdateView):
    """
    Only Admin & Manager can update.
    Both can update ANY deliverable.
    """
    model = Deliverable
    form_class = DeliverableForm
    template_name = "projects/deliverable_form.html"

    def get_queryset(self):
        qs = Deliverable.objects.select_related("project", "project__manager")
        user = self.request.user

        if is_admin(user) or is_manager(user):
            # Admin & Manager: all deliverables
            return qs
        return Deliverable.objects.none()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["project"] = self.object.project
        return kwargs

    def form_valid(self, form):
        """
        Handle:
        - WorkLog start/stop when status crosses IN_PROGRESS
        - first_started_at
        - delivered_at
        - ensure only ONE active worklog per user
        """
        deliverable = form.save(commit=False)
        user = self.request.user

        # Previous DB state
        old = Deliverable.objects.get(pk=deliverable.pk)
        old_status = old.status
        new_status = form.cleaned_data.get("status", old_status)

        # WorkLog should be attached to the assignee (worker),
        # not the manager who edits.
        work_user = deliverable.assigned_to or user

        # --------------------------------------------------------------------
        # 1) Moving INTO IN_PROGRESS -> create WorkLog
        # --------------------------------------------------------------------
        if new_status == DeliverableStatus.IN_PROGRESS and old_status != DeliverableStatus.IN_PROGRESS:
            if work_user:
                # Enforce "only one active worklog per user"
                if WorkLog.objects.filter(user=work_user, ended_at__isnull=True).exists():
                    messages.error(
                        self.request,
                        "This user already has another task or deliverable in progress.",
                    )
                    return redirect("projects:deliverable_detail", pk=deliverable.pk)

                # Set first_started_at only once
                if deliverable.first_started_at is None:
                    deliverable.first_started_at = timezone.now()

                # Create new WorkLog session
                WorkLog.objects.create(
                    user=work_user,
                    project=deliverable.project,
                    deliverable=deliverable,
                    started_at=timezone.now(),
                )

        # --------------------------------------------------------------------
        # 2) Leaving IN_PROGRESS -> close WorkLog
        # --------------------------------------------------------------------
        if old_status == DeliverableStatus.IN_PROGRESS and new_status != DeliverableStatus.IN_PROGRESS:
            if work_user:
                WorkLog.objects.filter(
                    user=work_user,
                    deliverable=deliverable,
                    ended_at__isnull=True,
                ).update(ended_at=timezone.now())

        # --------------------------------------------------------------------
        # 3) Delivered timestamp
        #    (form + status view already enforce "all tasks completed")
        # --------------------------------------------------------------------
        if new_status == DeliverableStatus.DELIVERED and deliverable.delivered_at is None:
            deliverable.delivered_at = timezone.now()

        # Save final status
        deliverable.status = new_status
        deliverable.save()
        form.save_m2m()

        messages.success(self.request, "Deliverable updated successfully.")
        return redirect("projects:deliverable_detail", pk=deliverable.pk)


class DeliverableDetailView(StaffAllMixin, DetailView):
    """
    Detail view for a single Deliverable.

    Visibility:
    - Admin: all deliverables
    - Manager: all deliverables
    - Employee: only deliverables assigned_to = user
    """
    model = Deliverable
    template_name = "projects/deliverable_detail.html"
    context_object_name = "deliverable"

    def get_queryset(self):
        qs = Deliverable.objects.select_related(
            "project",
            "project__client",
            "project__manager",
            "assigned_to",
        ).prefetch_related(
            "tasks__assigned_to"
        )

        user = self.request.user

        if is_admin(user) or is_manager(user):
            return qs
        elif is_employee(user):
            return qs.filter(assigned_to=user)
        return Deliverable.objects.none()


class DeliverableKanbanView(StaffAllMixin, TemplateView):
    """
    Kanban board for Deliverables.
    Columns = DeliverableStatus
    Cards = deliverables visible to current user.

    Visibility:
    - Admin/Manager: all deliverables
    - Employee: only assigned_to = user

    Only for projects that are NOT completed.
    """
    template_name = "projects/deliverable_kanban.html"

    def get_queryset(self):
        qs = Deliverable.objects.select_related(
            "project", "project__client", "assigned_to"
        )
        user = self.request.user

        # 🔹 Only deliverables for projects that are NOT completed
        qs = qs.exclude(project__status=ProjectStatus.COMPLETED)

        if is_admin(user) or is_manager(user):
            # full access (for all non-completed projects)
            pass
        elif is_employee(user):
            qs = qs.filter(assigned_to=user)
        else:
            qs = Deliverable.objects.none()

        # Order by due_date for nicer ordering inside columns
        qs = qs.order_by("due_date", "status", "created_at")

        # (Optional) keep extra filters if you ever add them in querystring
        status = self.request.GET.get("status")
        d_type = self.request.GET.get("type")
        if status:
            qs = qs.filter(status=status)
        if d_type:
            qs = qs.filter(type=d_type)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()

        deliverables_by_status = {}
        for key, label in DeliverableStatus.choices:
            deliverables_by_status[key] = qs.filter(status=key)

        context["deliverables_by_status"] = deliverables_by_status
        context["status_choices"] = DeliverableStatus.choices
        context["type_choices"] = DeliverableType.choices
        return context


class DeliverableStatusUpdateView(StaffAllMixin, View):

    def post(self, request, pk):
        deliverable = get_object_or_404(Deliverable, pk=pk)
        user = request.user
        new_status = request.POST.get("status")

        if is_employee(user) and deliverable.assigned_to != user:
            return JsonResponse({"success": False, "error": "Not allowed."}, status=403)

        valid = {c[0] for c in DeliverableStatus.choices}
        if new_status not in valid:
            return JsonResponse({"success": False, "error": "Invalid status"}, status=400)

        old_status = deliverable.status

        # --------------------------------------------------------------------
        # 1) Move INTO IN_PROGRESS → create new WorkLog
        # --------------------------------------------------------------------
        if new_status == DeliverableStatus.IN_PROGRESS and old_status != DeliverableStatus.IN_PROGRESS:

            if WorkLog.objects.filter(user=user, ended_at__isnull=True).exists():
                return JsonResponse({
                    "success": False,
                    "error": "You already have another task/deliverable in progress."
                }, status=400)

            if deliverable.first_started_at is None:
                deliverable.first_started_at = timezone.now()

            WorkLog.objects.create(
                user=user,
                project=deliverable.project,
                deliverable=deliverable,
                started_at=timezone.now()
            )

        # --------------------------------------------------------------------
        # 2) Leaving IN_PROGRESS → close WorkLog
        # --------------------------------------------------------------------
        if old_status == DeliverableStatus.IN_PROGRESS and new_status != DeliverableStatus.IN_PROGRESS:
            WorkLog.objects.filter(
                user=user,
                deliverable=deliverable,
                ended_at__isnull=True
            ).update(ended_at=timezone.now())

        # --------------------------------------------------------------------
        # 3) Delivered rule
        # --------------------------------------------------------------------
        if new_status == DeliverableStatus.DELIVERED and deliverable.delivered_at is None:
            deliverable.delivered_at = timezone.now()

        deliverable.status = new_status
        deliverable.save(update_fields=["status", "delivered_at", "first_started_at"])

        return JsonResponse({"success": True, "status": new_status})
