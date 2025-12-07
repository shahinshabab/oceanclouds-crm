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


