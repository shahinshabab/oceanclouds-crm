# common/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .roles import (
    ROLE_ADMIN,
    ROLE_MANAGER,
    ROLE_EMPLOYEE,
    user_has_role,
)
from django.contrib.auth.models import Group


class RolesRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Generic mixin – subclass and set allowed_roles.
    """
    allowed_roles = []

    # If you prefer redirect instead of 403, remove this line:
    raise_exception = True

    def test_func(self):
        return user_has_role(self.request.user, *self.allowed_roles)


class AdminOnlyMixin(RolesRequiredMixin):
    allowed_roles = [ROLE_ADMIN]


class AdminManagerMixin(RolesRequiredMixin):
    allowed_roles = [ROLE_ADMIN, ROLE_MANAGER]


class StaffAllMixin(RolesRequiredMixin):
    """
    Admin + Manager + Employee.
    """
    allowed_roles = [ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE]


class CRMManagerMixin(RolesRequiredMixin):
    """
    Manager who handles CRM (clients, leads, deals, invoices).
    Requires:
        - ROLE_MANAGER
        - Group = "CRM_MANAGER"
    """
    allowed_roles = [ROLE_MANAGER]

    def test_func(self):
        user = self.request.user
        if not user_has_role(user, ROLE_MANAGER):
            return False
        return Group.objects.filter(name="CRM_MANAGER", user=user).exists()


class ProjectManagerMixin(RolesRequiredMixin):
    """
    Manager who handles Projects (projects, tasks, deliverables).
    Requires:
        - ROLE_MANAGER
        - Group = "PROJECT_MANAGER"
    """
    allowed_roles = [ROLE_MANAGER]

    def test_func(self):
        user = self.request.user
        if not user_has_role(user, ROLE_MANAGER):
            return False
        return Group.objects.filter(name="PROJECT_MANAGER", user=user).exists()
