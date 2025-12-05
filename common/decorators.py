# common/decorators.py
from django.contrib.auth.decorators import login_required, user_passes_test
from .roles import user_has_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE

def roles_required(*roles):
    def check(user):
        return user_has_role(user, *roles)
    return login_required(user_passes_test(check, raise_exception=True))


admin_only = roles_required(ROLE_ADMIN)
admin_manager_only = roles_required(ROLE_ADMIN, ROLE_MANAGER)
staff_all = roles_required(ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE)
