# ui/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import Group

from common.roles import (
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
    user_has_role,
)


@login_required
def home(request):
    user = request.user

    # Base roles
    is_admin = user_has_role(user, ROLE_ADMIN)
    is_manager = user_has_role(user, ROLE_MANAGER)
    is_employee = user_has_role(user, ROLE_EMPLOYEE)

    # Manager sub-roles via Django Groups
    is_crm_manager = False
    is_project_manager = False

    if is_manager:
        is_crm_manager = Group.objects.filter(name="CRM_MANAGER", user=user).exists()
        is_project_manager = Group.objects.filter(name="PROJECT_MANAGER", user=user).exists()

    # Human-readable label for display
    if is_admin:
        role_label = "Admin"
    elif is_manager:
        if is_crm_manager and is_project_manager:
            role_label = "Manager (CRM & Projects)"
        elif is_crm_manager:
            role_label = "CRM Manager"
        elif is_project_manager:
            role_label = "Project Manager"
        else:
            role_label = "Manager"
    elif is_employee:
        role_label = "Employee"
    else:
        role_label = "User"

    context = {
        "role_label": role_label,
        "is_admin": is_admin,
        "is_manager": is_manager,
        "is_employee": is_employee,
        "is_crm_manager": is_crm_manager,
        "is_project_manager": is_project_manager,
    }
    return render(request, "ui/home.html", context)


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Welcome back!")
            return redirect("ui:home")  # redirect to dashboard/home

        else:
            messages.error(request, "Invalid username or password")

    return render(request, "ui/login.html")


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("ui:login")

