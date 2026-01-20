# ui/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import Group

from common.roles import user_has_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE

from crm.models import Client, Lead, Inquiry
from sales.models import Deal
from projects.models import (
    Project,
    Task,
    Deliverable,
    ProjectStatus,
    TaskStatus,
    DeliverableStatus,
)

from django.utils import timezone



def _get_month_info():
    """
    Returns:
      this_year, this_month, prev_year, prev_month
    """
    today = timezone.now().date()
    this_year = today.year
    this_month = today.month

    if this_month == 1:
        prev_year = this_year - 1
        prev_month = 12
    else:
        prev_year = this_year
        prev_month = this_month - 1

    return this_year, this_month, prev_year, prev_month


def _pct_change(current: int, prev: int) -> int:
    """
    Returns percentage change rounded to int.
    - If prev == 0 and current > 0 → 100
    - If both 0 → 0
    """
    if prev == 0:
        if current == 0:
            return 0
        return 100
    return round((current - prev) * 100 / prev)


@login_required
def home(request):
    user = request.user

    # ---- Roles ----
    is_admin = user_has_role(user, ROLE_ADMIN)
    is_manager = user_has_role(user, ROLE_MANAGER)
    is_employee = user_has_role(user, ROLE_EMPLOYEE)

    if is_admin:
        role_label = "Admin"
    elif is_manager:
        role_label = "Manager"
    elif is_employee:
        role_label = "Employee"
    else:
        role_label = "User"

    # Month info for comparisons
    this_year, this_month, prev_year, prev_month = _get_month_info()

    # ------------------------------------------------------------------
    # Default values (to avoid missing keys in context)
    # ------------------------------------------------------------------
    pending_projects_count = 0
    pending_tasks_count = 0
    pending_deliverables_count = 0

    # Row 2 (admin/manager) monthly totals + previous month + pct change
    total_leads_count = 0
    total_clients_count = 0
    total_deals_count = 0

    total_leads_prev_count = 0
    total_clients_prev_count = 0
    total_deals_prev_count = 0

    total_leads_pct_change = 0
    total_clients_pct_change = 0
    total_deals_pct_change = 0

    # Employee counts
    my_pending_tasks_count = 0
    my_pending_deliverables_count = 0
    my_inquiries_count = 0  # open/in-progress

    # Employee row 2 monthly totals + previous + pct
    my_completed_tasks_count = 0
    my_completed_deliverables_count = 0
    my_total_inquiries_count = 0

    my_completed_tasks_prev_count = 0
    my_completed_deliverables_prev_count = 0
    my_total_inquiries_prev_count = 0

    my_completed_tasks_pct_change = 0
    my_completed_deliverables_pct_change = 0
    my_total_inquiries_pct_change = 0

    pending_projects_list = None
    pending_tasks_list = None
    pending_deliverables_list = None

    my_pending_tasks_list = None
    my_pending_deliverables_list = None

    # ------------------------------------------------------------------
    # ADMIN
    # ------------------------------------------------------------------
    if is_admin:
        # Row 1: global current pending counts (no month comparison)
        pending_projects_count = Project.objects.exclude(
            status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
        ).count()

        pending_tasks_count = Task.objects.filter(
            status=TaskStatus.PENDING
        ).count()

        pending_deliverables_count = Deliverable.objects.filter(
            status=DeliverableStatus.PENDING
        ).count()

        # Row 2: monthly totals for all leads/clients/deals
        leads_qs = Lead.objects.all()
        clients_qs = Client.objects.all()
        deals_qs = Deal.objects.all()

        total_leads_count = leads_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_leads_prev_count = leads_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_leads_pct_change = _pct_change(total_leads_count, total_leads_prev_count)

        total_clients_count = clients_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_clients_prev_count = clients_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_clients_pct_change = _pct_change(
            total_clients_count, total_clients_prev_count
        )

        total_deals_count = deals_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_deals_prev_count = deals_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_deals_pct_change = _pct_change(total_deals_count, total_deals_prev_count)

        # Lists: global scope
        pending_projects_list = (
            Project.objects
            .exclude(status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED])
            .select_related("client", "manager")
            .order_by("due_date", "name")[:10]
        )

        pending_tasks_list = (
            Task.objects
            .filter(status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
            .select_related("project", "assigned_to")
            .order_by("due_date", "priority")[:10]
        )

        pending_deliverables_list = (
            Deliverable.objects
            .filter(status__in=[DeliverableStatus.PENDING, DeliverableStatus.IN_PROGRESS])
            .select_related("project", "assigned_to")
            .order_by("due_date", "name")[:10]
        )

    # ------------------------------------------------------------------
    # MANAGER
    # ------------------------------------------------------------------
    elif is_manager:
        # Row 1: manager's current pending counts
        pending_projects_count = Project.objects.filter(
            manager=user
        ).exclude(
            status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED]
        ).count()

        pending_tasks_count = Task.objects.filter(
            project__manager=user,
            status=TaskStatus.PENDING,
        ).count()

        pending_deliverables_count = Deliverable.objects.filter(
            project__manager=user,
            status=DeliverableStatus.PENDING,
        ).count()

        # Row 2: manager's monthly totals via Owned.owner
        leads_qs = Lead.objects.filter(owner=user)
        clients_qs = Client.objects.filter(owner=user)
        deals_qs = Deal.objects.filter(owner=user)

        total_leads_count = leads_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_leads_prev_count = leads_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_leads_pct_change = _pct_change(total_leads_count, total_leads_prev_count)

        total_clients_count = clients_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_clients_prev_count = clients_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_clients_pct_change = _pct_change(
            total_clients_count, total_clients_prev_count
        )

        total_deals_count = deals_qs.filter(
            created_at__year=this_year, created_at__month=this_month
        ).count()
        total_deals_prev_count = deals_qs.filter(
            created_at__year=prev_year, created_at__month=prev_month
        ).count()
        total_deals_pct_change = _pct_change(total_deals_count, total_deals_prev_count)

        # Lists: scoped to manager's projects
        pending_projects_list = (
            Project.objects
            .filter(manager=user)
            .exclude(status__in=[ProjectStatus.COMPLETED, ProjectStatus.CANCELLED])
            .select_related("client", "manager")
            .order_by("due_date", "name")[:10]
        )

        pending_tasks_list = (
            Task.objects
            .filter(
                project__manager=user,
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
            )
            .select_related("project", "assigned_to")
            .order_by("due_date", "priority")[:10]
        )

        pending_deliverables_list = (
            Deliverable.objects
            .filter(
                project__manager=user,
                status__in=[DeliverableStatus.PENDING, DeliverableStatus.IN_PROGRESS],
            )
            .select_related("project", "assigned_to")
            .order_by("due_date", "name")[:10]
        )

    # ------------------------------------------------------------------
    # EMPLOYEE
    # ------------------------------------------------------------------
    elif is_employee:
        # Row 1: current pending
        my_pending_tasks_count = Task.objects.filter(
            status=TaskStatus.PENDING,
            assigned_to=user,
        ).count()

        my_pending_deliverables_count = Deliverable.objects.filter(
            status=DeliverableStatus.PENDING,
            assigned_to=user,
        ).count()

        my_inquiries_count = Inquiry.objects.filter(
            handled_by=user,
            status__in=["open", "in_progress"],
        ).count()

        # Row 2: monthly completed + inquiries handled (this month vs prev)
        completed_tasks_qs = Task.objects.filter(
            status=TaskStatus.COMPLETED,
            assigned_to=user,
        )
        delivered_qs = Deliverable.objects.filter(
            status=DeliverableStatus.DELIVERED,
            assigned_to=user,
        )
        handled_inquiries_qs = Inquiry.objects.filter(handled_by=user)

        my_completed_tasks_count = completed_tasks_qs.filter(
            updated_at__year=this_year, updated_at__month=this_month
        ).count()
        my_completed_tasks_prev_count = completed_tasks_qs.filter(
            updated_at__year=prev_year, updated_at__month=prev_month
        ).count()
        my_completed_tasks_pct_change = _pct_change(
            my_completed_tasks_count, my_completed_tasks_prev_count
        )

        my_completed_deliverables_count = delivered_qs.filter(
            updated_at__year=this_year, updated_at__month=this_month
        ).count()
        my_completed_deliverables_prev_count = delivered_qs.filter(
            updated_at__year=prev_year, updated_at__month=prev_month
        ).count()
        my_completed_deliverables_pct_change = _pct_change(
            my_completed_deliverables_count, my_completed_deliverables_prev_count
        )

        my_total_inquiries_count = handled_inquiries_qs.filter(
            updated_at__year=this_year, updated_at__month=this_month
        ).count()
        my_total_inquiries_prev_count = handled_inquiries_qs.filter(
            updated_at__year=prev_year, updated_at__month=prev_month
        ).count()
        my_total_inquiries_pct_change = _pct_change(
            my_total_inquiries_count, my_total_inquiries_prev_count
        )

        # Row 3: lists (only own items)
        my_pending_tasks_list = (
            Task.objects
            .filter(
                status__in=[TaskStatus.PENDING, TaskStatus.IN_PROGRESS],
                assigned_to=user,
            )
            .select_related("project")
            .order_by("due_date", "priority")[:10]
        )

        my_pending_deliverables_list = (
            Deliverable.objects
            .filter(
                status__in=[DeliverableStatus.PENDING, DeliverableStatus.IN_PROGRESS],
                assigned_to=user,
            )
            .select_related("project")
            .order_by("due_date", "name")[:10]
        )

    # ------------------------------------------------------------------
    # Fallback (user without any role)
    # ------------------------------------------------------------------
    else:
        pass

    context = {
        "role_label": role_label,
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_employee": is_employee,

        # Admin/Manager counts (row 1)
        "pending_projects_count": pending_projects_count,
        "pending_tasks_count": pending_tasks_count,
        "pending_deliverables_count": pending_deliverables_count,

        # Admin/Manager monthly totals (row 2)
        "total_leads_count": total_leads_count,
        "total_clients_count": total_clients_count,
        "total_deals_count": total_deals_count,
        "total_leads_prev_count": total_leads_prev_count,
        "total_clients_prev_count": total_clients_prev_count,
        "total_deals_prev_count": total_deals_prev_count,
        "total_leads_pct_change": total_leads_pct_change,
        "total_clients_pct_change": total_clients_pct_change,
        "total_deals_pct_change": total_deals_pct_change,

        # Employee counts (row 1)
        "my_pending_tasks_count": my_pending_tasks_count,
        "my_pending_deliverables_count": my_pending_deliverables_count,
        "my_inquiries_count": my_inquiries_count,

        # Employee monthly totals (row 2)
        "my_completed_tasks_count": my_completed_tasks_count,
        "my_completed_deliverables_count": my_completed_deliverables_count,
        "my_total_inquiries_count": my_total_inquiries_count,
        "my_completed_tasks_prev_count": my_completed_tasks_prev_count,
        "my_completed_deliverables_prev_count": my_completed_deliverables_prev_count,
        "my_total_inquiries_prev_count": my_total_inquiries_prev_count,
        "my_completed_tasks_pct_change": my_completed_tasks_pct_change,
        "my_completed_deliverables_pct_change": my_completed_deliverables_pct_change,
        "my_total_inquiries_pct_change": my_total_inquiries_pct_change,

        # Lists
        "pending_projects_list": pending_projects_list,
        "pending_tasks_list": pending_tasks_list,
        "pending_deliverables_list": pending_deliverables_list,
        "my_pending_tasks_list": my_pending_tasks_list,
        "my_pending_deliverables_list": my_pending_deliverables_list,
    }

    return render(request, "ui/home.html", context)



def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Welcome back!" ,extra_tags="scope:auth")
            return redirect("ui:home")  # redirect to dashboard/home

        else:
            messages.error(request, "Invalid username or password", extra_tags="scope:auth")

    return render(request, "ui/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.", extra_tags="scope:auth")
    return redirect("ui:login")

