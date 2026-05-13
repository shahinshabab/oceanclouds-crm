from django.urls import path

from .views import (
    UserListView,
    UserCreateView,
    UserUpdateView,
    RoleListView,
    RoleCreateView,
    RoleUpdateView,
    SystemSettingUpdateView,
)

app_name = "adminpanel"

urlpatterns = [
    # Users
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/create/", UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", UserUpdateView.as_view(), name="user_edit"),

    # Roles / Groups
    path("roles/", RoleListView.as_view(), name="role_list"),
    path("roles/create/", RoleCreateView.as_view(), name="role_create"),
    path("roles/<int:pk>/edit/", RoleUpdateView.as_view(), name="role_edit"),

    # System Settings singleton
    path("settings/", SystemSettingUpdateView.as_view(), name="system_settings"),
]