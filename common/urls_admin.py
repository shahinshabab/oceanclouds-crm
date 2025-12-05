# common/urls_admin.py
from django.urls import path
from . import views_admin as admin_views

app_name = "adminpanel"

urlpatterns = [
    # Users
    path("users/", admin_views.UserListView.as_view(), name="user_list"),
    path("users/create/", admin_views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", admin_views.UserUpdateView.as_view(), name="user_edit"),

    # Roles & Permissions
    path("roles/", admin_views.RoleListView.as_view(), name="role_list"),
    path("roles/create/", admin_views.RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/edit/", admin_views.RoleUpdateView.as_view(), name="role_edit"),

    # System Settings (singleton)
    path("settings/", admin_views.SystemSettingUpdateView.as_view(), name="system_settings"),
]
