# common/decorators.py
from django.contrib.auth.decorators import login_required, user_passes_test
from .roles import (
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_EMPLOYEE,
    ROLE_PROJECT_MANAGER,
    user_has_role,
)

def roles_required(*roles):
    def check(user):
        return user_has_role(user, *roles)
    return login_required(user_passes_test(check, raise_exception=True))


admin_only = roles_required(ROLE_ADMIN)
admin_manager_only = roles_required(ROLE_ADMIN, ROLE_CRM_MANAGER, ROLE_PROJECT_MANAGER)
staff_all = roles_required(
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_PROJECT_MANAGER,
    ROLE_EMPLOYEE,
)
