# common/views_admin.py
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import (
    ListView,
    CreateView,
    UpdateView,
)
from django.shortcuts import redirect

from .forms import (
    UserCreateForm,
    UserUpdateForm,
    RoleForm,
    SystemSettingForm,
)
from .models import SystemSetting

User = get_user_model()


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        # Only staff/admin can access these pages
        return self.request.user.is_staff or self.request.user.is_superuser


# ---------- Users ---------- #

class UserListView(StaffRequiredMixin, ListView):
    model = User
    template_name = "admin/user_list.html"
    context_object_name = "users"
    paginate_by = 25

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(username__icontains=q) | qs.filter(
                first_name__icontains=q
            ) | qs.filter(last_name__icontains=q) | qs.filter(email__icontains=q)
        return qs


class UserCreateView(StaffRequiredMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "admin/user_form.html"
    success_url = reverse_lazy("adminpanel:user_list")


class UserUpdateView(StaffRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "admin/user_form.html"
    success_url = reverse_lazy("adminpanel:user_list")


# ---------- Roles & Permissions (Groups) ---------- #

class RoleListView(StaffRequiredMixin, ListView):
    model = Group
    template_name = "admin/role_list.html"
    context_object_name = "roles"


class RoleCreateView(StaffRequiredMixin, CreateView):
    model = Group
    form_class = RoleForm
    template_name = "admin/role_form.html"
    success_url = reverse_lazy("adminpanel:role_list")


class RoleUpdateView(StaffRequiredMixin, UpdateView):
    model = Group
    form_class = RoleForm
    template_name = "admin/role_form.html"
    success_url = reverse_lazy("adminpanel:role_list")


# ---------- System Settings ---------- #

class SystemSettingUpdateView(StaffRequiredMixin, UpdateView):
    model = SystemSetting
    form_class = SystemSettingForm
    template_name = "admin/system_settings_form.html"
    success_url = reverse_lazy("adminpanel:system_settings")

    def get_object(self, queryset=None):
        obj, _ = SystemSetting.objects.get_or_create(pk=1)
        return obj

    # Optional: redirect GET to the singleton instance URL if you want /settings/ to always work
    # but with UpdateView and get_object like this, you don't need a pk in URL.
