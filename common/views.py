# common/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from .models import Notification
from datetime import date
import re
from statistics import mean
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Q
from .forms import AnalyticsReportFilterForm
from crm.models import Client, Lead, Inquiry, ClientReview
from weasyprint import HTML  # pip install weasyprint

from projects.models import (
    Project,
    Task,
    Deliverable,
    FileType,
    DeliverableType,
    TaskStatus,
    DeliverableStatus,
    ProjectStatus,
    WorkLog,
)
from sales.models import (
    Deal,
    Proposal,
    Contract,
    Invoice,
    Payment,
    DealStage,
    ProposalStatus,
    ContractStatus,
)
User = get_user_model()
NUMBER_RE = re.compile(r"(\d+)")


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "common/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 20  # changed from 25 to 20

    def get_queryset(self):
        user = self.request.user
        qs = Notification.objects.filter(recipient=user)

        # --- Search ---
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(message__icontains=q)
                | Q(actor__username__icontains=q)
                | Q(actor__first_name__icontains=q)
                | Q(actor__last_name__icontains=q)
            )

        # --- Category filter (all / assigned / overdue / deliverable_overdue) ---
        category = self.request.GET.get("category", "all")
        if category == "assigned":
            qs = qs.filter(
                notif_type__in=[
                    Notification.Type.PROJECT_ASSIGNED,
                    Notification.Type.TASK_ASSIGNED,
                ]
            )
        elif category == "overdue":
            qs = qs.filter(notif_type=Notification.Type.OVERDUE)
        elif category == "deliverable_overdue":
            qs = qs.filter(notif_type=Notification.Type.DELIVERABLE_OVERDUE)
        # "all" = no extra filter

        # --- Read status filter (all / unread / read) ---
        status = self.request.GET.get("status", "all")
        if status == "unread":
            qs = qs.filter(is_read=False)
        elif status == "read":
            qs = qs.filter(is_read=True)

        # Newest first
        qs = qs.order_by("-created_at")

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Preserve current filters for the template
        context["q"] = self.request.GET.get("q", "").strip()
        context["category"] = self.request.GET.get("category", "all")
        context["status"] = self.request.GET.get("status", "all")

        # Options for dropdowns
        context["category_choices"] = [
            ("all", "All notifications"),
            ("assigned", "Assigned (projects & tasks)"),
            ("overdue", "Task overdue"),
            ("deliverable_overdue", "Deliverable overdue"),
        ]

        context["status_choices"] = [
            ("all", "All (read & unread)"),
            ("unread", "Unread only"),
            ("read", "Read only"),
        ]

        return context



@login_required
def mark_notification_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)

    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])

    # If it's an AJAX request (header bell dropdown), return JSON
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True})

    # Otherwise (normal POST from list view), redirect back
    next_url = (
        request.POST.get("next")
        or request.META.get("HTTP_REFERER")
        or reverse("common:notification_list")
    )
    return redirect(next_url)

# ---------------------------------------------------------
# Helper: build CRM + Sales report
# ---------------------------------------------------------
def build_crm_sales_report(*, date_from, date_to, selected_user, all_manager_qs):
    """
    Returns a dict with CRM + Sales metrics for:
      - a specific owner (selected_user), OR
      - all manager owners (all_manager_qs), when selected_user is None.
    """

    def apply_filters(qs, *, date_field, is_date_field=False):
        # owner filter
        if selected_user is not None:
            qs = qs.filter(owner=selected_user)
        else:
            # All managers – restrict to records owned by any manager
            qs = qs.filter(owner__in=all_manager_qs)

        # date range filter
        if date_from:
            lookup = f"{date_field}__gte" if is_date_field else f"{date_field}__date__gte"
            qs = qs.filter(**{lookup: date_from})

        if date_to:
            lookup = f"{date_field}__lte" if is_date_field else f"{date_field}__date__lte"
            qs = qs.filter(**{lookup: date_to})

        return qs

    # ---- CRM: Inquiries ----
    inquiries_qs = apply_filters(Inquiry.objects.all(), date_field="created_at", is_date_field=False)
    total_inquiries = inquiries_qs.count()
    converted_inquiries = inquiries_qs.filter(status="converted").count()

    channel_label_map = dict(Inquiry.CHANNEL_CHOICES)
    inquiries_by_channel = list(
        inquiries_qs.values("channel")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    for row in inquiries_by_channel:
        row["label"] = channel_label_map.get(row["channel"], row["channel"])

    # ---- CRM: Leads ----
    leads_qs = apply_filters(Lead.objects.all(), date_field="created_at", is_date_field=False)
    total_leads = leads_qs.count()
    leads_converted = leads_qs.filter(Q(status="converted") | Q(client__isnull=False)).distinct().count()

    source_label_map = dict(Lead.SOURCE_CHOICES)
    leads_by_source = list(
        leads_qs.values("source")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    for row in leads_by_source:
        row["label"] = source_label_map.get(row["source"], row["source"])

    # ---- CRM: Clients ----
    clients_qs = apply_filters(Client.objects.all(), date_field="created_at", is_date_field=False)
    total_clients = clients_qs.count()

    # ---- CRM: Reviews ----
    reviews_qs = apply_filters(ClientReview.objects.all(), date_field="created_at", is_date_field=False)
    total_reviews = reviews_qs.count()
    reviews_with_rating = reviews_qs.exclude(rating__isnull=True)
    avg_rating = reviews_with_rating.aggregate(avg=Sum("rating"))["avg"]
    if avg_rating and reviews_with_rating.count():
        avg_rating = round(avg_rating / reviews_with_rating.count(), 2)
    else:
        avg_rating = None

    # ---- Sales: Deals ----
    deals_qs = apply_filters(Deal.objects.all(), date_field="created_at", is_date_field=False)
    total_deals = deals_qs.count()
    deals_won = deals_qs.filter(stage=DealStage.WON).count()
    deals_lost = deals_qs.filter(stage=DealStage.LOST).count()
    deals_on_hold = deals_qs.filter(stage=DealStage.ON_HOLD).count()

    # ---- Sales: Proposals ----
    proposals_qs = apply_filters(Proposal.objects.all(), date_field="created_at", is_date_field=False)
    total_proposals = proposals_qs.count()
    proposals_sent = proposals_qs.filter(
        status__in=[ProposalStatus.SENT, ProposalStatus.ACCEPTED, ProposalStatus.REJECTED]
    ).count()
    proposals_accepted = proposals_qs.filter(status=ProposalStatus.ACCEPTED).count()
    proposals_rejected = proposals_qs.filter(status=ProposalStatus.REJECTED).count()

    # ---- Sales: Contracts ----
    contracts_qs = apply_filters(Contract.objects.all(), date_field="created_at", is_date_field=False)
    total_contracts = contracts_qs.count()
    signed_contracts = contracts_qs.filter(status=ContractStatus.SIGNED).count()

    # ---- Sales: Invoices & Payments ----
    invoices_qs = apply_filters(Invoice.objects.all(), date_field="issue_date", is_date_field=True)
    total_invoices = invoices_qs.count()
    total_invoiced_amount = invoices_qs.aggregate(total=Sum("total"))["total"] or 0
    total_amount_paid = invoices_qs.aggregate(total=Sum("amount_paid"))["total"] or 0
    outstanding_balance = (total_invoiced_amount or 0) - (total_amount_paid or 0)

    payments_qs = apply_filters(Payment.objects.all(), date_field="date", is_date_field=True)
    total_payments = payments_qs.count()
    total_payments_amount = payments_qs.aggregate(total=Sum("amount"))["total"] or 0

    has_any_data = any([
        total_inquiries,
        total_leads,
        total_clients,
        total_reviews,
        total_deals,
        total_proposals,
        total_contracts,
        total_invoices,
        total_payments,
    ])

    report = {
        "has_any_data": bool(has_any_data),
        "crm": {
            "inquiries": {
                "total": total_inquiries,
                "converted": converted_inquiries,
                "by_channel": inquiries_by_channel,
            },
            "leads": {
                "total": total_leads,
                "converted_to_client": leads_converted,
                "by_source": leads_by_source,
            },
            "clients": {
                "total": total_clients,
            },
            "reviews": {
                "total": total_reviews,
                "avg_rating": avg_rating,
            },
        },
        "sales": {
            "deals": {
                "total": total_deals,
                "won": deals_won,
                "lost": deals_lost,
                "on_hold": deals_on_hold,
            },
            "proposals": {
                "total": total_proposals,
                "sent": proposals_sent,
                "accepted": proposals_accepted,
                "rejected": proposals_rejected,
            },
            "contracts": {
                "total": total_contracts,
                "signed": signed_contracts,
            },
            "invoices": {
                "total": total_invoices,
                "total_invoiced_amount": total_invoiced_amount,
                "total_amount_paid": total_amount_paid,
                "outstanding_balance": outstanding_balance,
            },
            "payments": {
                "total": total_payments,
                "total_amount": total_payments_amount,
            },
        },
    }

    return report


# ---------------------------------------------------------
# Helper: build Performance report (Tasks + Deliverables + WorkLog)
# ---------------------------------------------------------
def build_performance_report(*, date_from, date_to, selected_user):
    """
    Returns a dict with performance metrics for a single user:
      - If Manager:
          * tasks/deliverables CREATED (owner=selected_user)
      - If Employee (or non-manager):
          * tasks/deliverables ASSIGNED (assigned_to=selected_user)
      - Always:
          * WorkLog-based time metrics
    """
    if not selected_user:
        return {
            "has_any_data": False,
            "mode": None,
        }

    # Role detection
    is_manager = selected_user.groups.filter(name="Manager").exists()
    is_employee = selected_user.groups.filter(name="Employee").exists()
    mode = "manager" if is_manager and not is_employee else "employee"

    def apply_dt_date(qs, field_name="created_at"):
        if date_from:
            qs = qs.filter(**{f"{field_name}__date__gte": date_from})
        if date_to:
            qs = qs.filter(**{f"{field_name}__date__lte": date_to})
        return qs

    # ---- Base querysets based on mode ----
    if mode == "manager":
        # Manager creates tasks/deliverables
        base_tasks_qs = Task.objects.filter(owner=selected_user)
        base_deliv_qs = Deliverable.objects.filter(owner=selected_user)
    else:
        # Employee works on tasks/deliverables assigned to them
        base_tasks_qs = Task.objects.filter(assigned_to=selected_user)
        base_deliv_qs = Deliverable.objects.filter(assigned_to=selected_user)

    tasks_qs = apply_dt_date(base_tasks_qs, "created_at")
    deliv_qs = apply_dt_date(base_deliv_qs, "created_at")

    tasks_total = tasks_qs.count()
    deliv_total = deliv_qs.count()

    # ---- Status breakdown ----
    task_status_label = dict(TaskStatus.choices)
    tasks_by_status = list(
        tasks_qs.values("status")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    for row in tasks_by_status:
        row["label"] = task_status_label.get(row["status"], row["status"])

    deliv_status_label = dict(DeliverableStatus.choices)
    deliverables_by_status = list(
        deliv_qs.values("status")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    for row in deliverables_by_status:
        row["label"] = deliv_status_label.get(row["status"], row["status"])

    # ---- WorkLog metrics ----
    logs_qs = WorkLog.objects.filter(user=selected_user)
    logs_qs = apply_dt_date(logs_qs, "started_at")

    total_seconds = 0
    day_set = set()

    for log in logs_qs:
        total_seconds += log.duration_seconds
        day_set.add(log.started_at.date())

    sessions_count = logs_qs.count()
    days_with_activity = len(day_set)
    total_hours = total_seconds / 3600 if total_seconds else 0
    avg_hours_per_active_day = (total_hours / days_with_activity) if days_with_activity else 0

    # ---- Timing: delay to start & time to complete ----
    delay_seconds_list = []
    completion_seconds_list = []

    # Delay: created_at -> first_started_at
    for t in tasks_qs.exclude(first_started_at__isnull=True):
        delta = t.first_started_at - t.created_at
        if delta.total_seconds() > 0:
            delay_seconds_list.append(delta.total_seconds())

    for d in deliv_qs.exclude(first_started_at__isnull=True):
        delta = d.first_started_at - d.created_at
        if delta.total_seconds() > 0:
            delay_seconds_list.append(delta.total_seconds())

    # Completion time: first_started_at -> completed/delivered
    for t in tasks_qs.exclude(first_started_at__isnull=True).exclude(completed_at__isnull=True):
        delta = t.completed_at - t.first_started_at
        if delta.total_seconds() > 0:
            completion_seconds_list.append(delta.total_seconds())

    for d in deliv_qs.exclude(first_started_at__isnull=True).exclude(delivered_at__isnull=True):
        delta = d.delivered_at - d.first_started_at
        if delta.total_seconds() > 0:
            completion_seconds_list.append(delta.total_seconds())

    if delay_seconds_list:
        avg_start_delay_hours = (sum(delay_seconds_list) / len(delay_seconds_list)) / 3600
    else:
        avg_start_delay_hours = 0

    if completion_seconds_list:
        avg_completion_time_hours = (sum(completion_seconds_list) / len(completion_seconds_list)) / 3600
    else:
        avg_completion_time_hours = 0

    # ---- Completion by category (Task.type / Deliverable.type) ----
    filetype_label = dict(FileType.choices)
    deliverabletype_label = dict(DeliverableType.choices)

    task_type_map = {}
    for t in tasks_qs.exclude(first_started_at__isnull=True).exclude(completed_at__isnull=True):
        delta = t.completed_at - t.first_started_at
        sec = delta.total_seconds()
        if sec <= 0:
            continue
        task_type_map.setdefault(t.type, []).append(sec)

    task_type_completion = []
    for code, secs in task_type_map.items():
        hours = (sum(secs) / len(secs)) / 3600
        task_type_completion.append(
            {"type": code, "label": filetype_label.get(code, code), "avg_hours": hours}
        )

    deliv_type_map = {}
    for d in deliv_qs.exclude(first_started_at__isnull=True).exclude(delivered_at__isnull=True):
        delta = d.delivered_at - d.first_started_at
        sec = delta.total_seconds()
        if sec <= 0:
            continue
        deliv_type_map.setdefault(d.type, []).append(sec)

    deliverable_type_completion = []
    for code, secs in deliv_type_map.items():
        hours = (sum(secs) / len(secs)) / 3600
        deliverable_type_completion.append(
            {"type": code, "label": deliverabletype_label.get(code, code), "avg_hours": hours}
        )

    has_any_data = any([tasks_total, deliv_total, sessions_count])

    report = {
        "has_any_data": bool(has_any_data),
        "mode": mode,  # 'manager' or 'employee'
        "summary": {
            "tasks_count": tasks_total,
            "deliverables_count": deliv_total,
        },
        "tasks": {
            "total": tasks_total,
            "by_status": tasks_by_status,
        },
        "deliverables": {
            "total": deliv_total,
            "by_status": deliverables_by_status,
        },
        "worklog": {
            "sessions": sessions_count,
            "total_seconds": total_seconds,
            "total_hours": total_hours,
            "days_with_activity": days_with_activity,
            "avg_hours_per_active_day": avg_hours_per_active_day,
        },
        "timing": {
            "avg_start_delay_hours": avg_start_delay_hours,
            "avg_completion_time_hours": avg_completion_time_hours,
            "task_type_completion": task_type_completion,
            "deliverable_type_completion": deliverable_type_completion,
        },
    }
    return report


# ---------------------------------------------------------
# Main HTML view
# ---------------------------------------------------------
@login_required
def analytics_report(request):
    form = AnalyticsReportFilterForm(request.GET or None)
    report = None
    report_type = None
    selected_user = None
    subject_label = None
    show_no_data = False

    if form.is_valid():
        report_type = form.cleaned_data.get("report_type")
        employee_obj = form.cleaned_data.get("employee")  # User instance or None
        date_from = form.cleaned_data.get("date_from")
        date_to = form.cleaned_data.get("date_to")

        selected_user = employee_obj  # use directly

        all_manager_qs = User.objects.filter(groups__name="Manager").distinct()

        if report_type == AnalyticsReportFilterForm.REPORT_CRM:
            report = build_crm_sales_report(
                date_from=date_from,
                date_to=date_to,
                selected_user=selected_user,
                all_manager_qs=all_manager_qs,
            )
            show_no_data = not report["has_any_data"]

            if selected_user:
                subject_label = selected_user.get_full_name() or selected_user.username
            else:
                subject_label = "All Managers"

        elif report_type == AnalyticsReportFilterForm.REPORT_PERFORMANCE:
            if not selected_user:
                report = None
                show_no_data = True
                subject_label = "Please select a Manager or Employee"
            else:
                report = build_performance_report(
                    date_from=date_from,
                    date_to=date_to,
                    selected_user=selected_user,
                )
                show_no_data = not report["has_any_data"]
                subject_label = selected_user.get_full_name() or selected_user.username

    context = {
        "form": form,
        "report_type": report_type,
        "report": report,
        "selected_user": selected_user,
        "subject_label": subject_label,
        "show_no_data": show_no_data,
    }
    return render(request, "ui/analytics_reports.html", context)



# ---------------------------------------------------------
# PDF view
# ---------------------------------------------------------
@login_required
def analytics_report_pdf(request):
    form = AnalyticsReportFilterForm(request.GET or None)
    if not form.is_valid():
        return redirect("common:analytics_report")

    report_type = form.cleaned_data.get("report_type")
    employee_obj = form.cleaned_data.get("employee")  # User or None
    date_from = form.cleaned_data.get("date_from")
    date_to = form.cleaned_data.get("date_to")

    selected_user = employee_obj
    all_manager_qs = User.objects.filter(groups__name="Manager").distinct()

    report = None
    subject_label = None

    if report_type == AnalyticsReportFilterForm.REPORT_CRM:
        report = build_crm_sales_report(
            date_from=date_from,
            date_to=date_to,
            selected_user=selected_user,
            all_manager_qs=all_manager_qs,
        )
        if selected_user:
            subject_label = selected_user.get_full_name() or selected_user.username
        else:
            subject_label = "All Managers"
        filename = "crm-analytics-report.pdf"

    elif report_type == AnalyticsReportFilterForm.REPORT_PERFORMANCE:
        if not selected_user:
            return redirect("common:analytics_report")

        report = build_performance_report(
            date_from=date_from,
            date_to=date_to,
            selected_user=selected_user,
        )
        subject_label = selected_user.get_full_name() or selected_user.username
        filename = "performance-report.pdf"
    else:
        return redirect("common:analytics_report")

    html_string = render_to_string(
        "ui/analytics_reports_pdf.html",
        {
            "form": form,
            "report_type": report_type,
            "report": report,
            "subject_label": subject_label,
        },
        request=request,
    )
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf_bytes = html.write_pdf()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def parse_int_from_text(text: str) -> int:
    if not text:
        return 0
    m = NUMBER_RE.search(text)
    return int(m.group(1)) if m else 0


# ---------- metrics builder (same as before) ----------

def build_project_metrics(project_qs):
    metrics = []

    project_qs = project_qs.select_related("client", "manager").prefetch_related(
        "tasks",
        "deliverables",
        "work_logs",
    )

    for project in project_qs:
        tasks = list(project.tasks.all())
        deliverables = list(project.deliverables.all())

        task_total = len(tasks)
        deliv_total = len(deliverables)

        completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        delivered_delivs = sum(
            1 for d in deliverables if d.status == DeliverableStatus.DELIVERED
        )

        # --- delay to start (task / deliverable) ---
        task_start_delays = []
        for t in tasks:
            if t.first_started_at and t.created_at:
                delta = (t.first_started_at - t.created_at).total_seconds()
                if delta >= 0:
                    task_start_delays.append(delta)

        deliverable_start_delays = []
        for d in deliverables:
            if d.first_started_at and d.created_at:
                delta = (d.first_started_at - d.created_at).total_seconds()
                if delta >= 0:
                    deliverable_start_delays.append(delta)

        avg_task_start_delay_hours = (
            mean(task_start_delays) / 3600 if task_start_delays else None
        )
        avg_deliv_start_delay_hours = (
            mean(deliverable_start_delays) / 3600 if deliverable_start_delays else None
        )

        # --- avg task completion time (photo vs video) ---
        image_task_durations = []
        video_task_durations = []

        for t in tasks:
            if t.first_started_at and t.completed_at:
                duration = (t.completed_at - t.first_started_at).total_seconds()
                if duration < 0:
                    continue
                if t.type == FileType.IMAGE:
                    image_task_durations.append(duration)
                elif t.type == FileType.VIDEO:
                    video_task_durations.append(duration)

        avg_image_task_hours = (
            mean(image_task_durations) / 3600 if image_task_durations else None
        )
        avg_video_task_hours = (
            mean(video_task_durations) / 3600 if video_task_durations else None
        )

        # --- avg deliverable completion time (by category) ---
        digital_durations = []
        physical_durations = []
        mixed_durations = []

        for d in deliverables:
            if d.first_started_at and d.delivered_at:
                duration = (d.delivered_at - d.first_started_at).total_seconds()
                if duration < 0:
                    continue
                if d.type == DeliverableType.DIGITAL:
                    digital_durations.append(duration)
                elif d.type == DeliverableType.PHYSICAL:
                    physical_durations.append(duration)
                elif d.type == DeliverableType.MIXED:
                    mixed_durations.append(duration)

        avg_digital_deliv_hours = (
            mean(digital_durations) / 3600 if digital_durations else None
        )
        avg_physical_deliv_hours = (
            mean(physical_durations) / 3600 if physical_durations else None
        )
        avg_mixed_deliv_hours = (
            mean(mixed_durations) / 3600 if mixed_durations else None
        )

        # --- total file counts by type from Task.count ---
        image_file_count = 0
        video_file_count = 0

        for t in tasks:
            c = parse_int_from_text(t.count)
            if t.type == FileType.IMAGE:
                image_file_count += c
            elif t.type == FileType.VIDEO:
                video_file_count += c

        total_file_count = image_file_count + video_file_count

        # --- total deliverables size (MB) ---
        total_bytes = 0
        for d in deliverables:
            if d.file and hasattr(d.file, "size"):
                total_bytes += d.file.size or 0
        total_deliverable_size_mb = total_bytes / (1024 * 1024) if total_bytes else 0

        metrics.append(
            {
                "project": project,
                "progress_percent": project.progress_percent,
                "tasks_completed": completed_tasks,
                "tasks_total": task_total,
                "deliverables_delivered": delivered_delivs,
                "deliverables_total": deliv_total,
                "avg_task_start_delay_hours": avg_task_start_delay_hours,
                "avg_deliv_start_delay_hours": avg_deliv_start_delay_hours,
                "avg_image_task_hours": avg_image_task_hours,
                "avg_video_task_hours": avg_video_task_hours,
                "avg_digital_deliv_hours": avg_digital_deliv_hours,
                "avg_physical_deliv_hours": avg_physical_deliv_hours,
                "avg_mixed_deliv_hours": avg_mixed_deliv_hours,
                "image_file_count": image_file_count,
                "video_file_count": video_file_count,
                "total_file_count": total_file_count,
                "total_deliverable_size_mb": total_deliverable_size_mb,
            }
        )

    return metrics


@login_required
def project_report(request):
    """
    Report page:
    - projects started within period
    - projects completed within period (status=COMPLETED and at least
      one task.completed_at or deliverable.delivered_at in the period)
    """
    status_filter = request.GET.get("status", "")
    date_from_raw = request.GET.get("date_from", "")
    date_to_raw = request.GET.get("date_to", "")

    today = timezone.localdate()

    if date_from_raw:
        date_from = parse_date(date_from_raw)
    else:
        date_from = today.replace(day=1)

    if date_to_raw:
        date_to = parse_date(date_to_raw)
    else:
        date_to = today

    if not date_from:
        date_from = today.replace(day=1)
    if not date_to:
        date_to = today

    projects = Project.objects.all()
    if status_filter:
        projects = projects.filter(status=status_filter)

    # ----- started in range (by start_date) -----
    started_projects_qs = projects.filter(
        start_date__isnull=False,
        start_date__gte=date_from,
        start_date__lte=date_to,
    )
    started_metrics = build_project_metrics(started_projects_qs)

    # ----- completed in range, WITHOUT snapshot -----
    # projects that are COMPLETED and have some completion event in the period
    task_project_ids = Task.objects.filter(
        status=TaskStatus.COMPLETED,
        completed_at__date__gte=date_from,
        completed_at__date__lte=date_to,
    ).values_list("project_id", flat=True)

    deliverable_project_ids = Deliverable.objects.filter(
        status=DeliverableStatus.DELIVERED,
        delivered_at__date__gte=date_from,
        delivered_at__date__lte=date_to,
    ).values_list("project_id", flat=True)

    completed_ids = set(task_project_ids) | set(deliverable_project_ids)

    completed_projects_qs = projects.filter(
        status=ProjectStatus.COMPLETED,
        id__in=completed_ids,
    ).distinct()

    completed_metrics = build_project_metrics(completed_projects_qs)

    context = {
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "started_metrics": started_metrics,
        "completed_metrics": completed_metrics,
        "project_status_choices": ProjectStatus.choices,
    }
    return render(request, "ui/project_report.html", context)


@login_required
def project_report_pdf(request):
    status_filter = request.GET.get("status", "")
    date_from_raw = request.GET.get("date_from", "")
    date_to_raw = request.GET.get("date_to", "")

    today = timezone.localdate()

    if date_from_raw:
        date_from = parse_date(date_from_raw)
    else:
        date_from = today.replace(day=1)

    if date_to_raw:
        date_to = parse_date(date_to_raw)
    else:
        date_to = today

    if not date_from:
        date_from = today.replace(day=1)
    if not date_to:
        date_to = today

    projects = Project.objects.all()
    if status_filter:
        projects = projects.filter(status=status_filter)

    started_projects_qs = projects.filter(
        start_date__isnull=False,
        start_date__gte=date_from,
        start_date__lte=date_to,
    )
    started_metrics = build_project_metrics(started_projects_qs)

    task_project_ids = Task.objects.filter(
        status=TaskStatus.COMPLETED,
        completed_at__date__gte=date_from,
        completed_at__date__lte=date_to,
    ).values_list("project_id", flat=True)

    deliverable_project_ids = Deliverable.objects.filter(
        status=DeliverableStatus.DELIVERED,
        delivered_at__date__gte=date_from,
        delivered_at__date__lte=date_to,
    ).values_list("project_id", flat=True)

    completed_ids = set(task_project_ids) | set(deliverable_project_ids)

    completed_projects_qs = projects.filter(
        status=ProjectStatus.COMPLETED,
        id__in=completed_ids,
    ).distinct()

    completed_metrics = build_project_metrics(completed_projects_qs)

    context = {
        "status_filter": status_filter,
        "date_from": date_from,
        "date_to": date_to,
        "started_metrics": started_metrics,
        "completed_metrics": completed_metrics,
    }

    html_string = render_to_string("ui/project_report_pdf.html", context, request=request)
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf = html.write_pdf()

    filename = f"project-report-{date_from}__{date_to}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
