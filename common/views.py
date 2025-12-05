# common/views.py
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = "common/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 25  # nice to have

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