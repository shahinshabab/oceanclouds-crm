# common/roles.py
from django.conf import settings

ROLE_ADMIN = "Admin"
ROLE_MANAGER = "Manager"
ROLE_EMPLOYEE = "Employee"

ROLE_ALL = [ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE]

def user_has_role(user, *roles):
    """
    Returns True if user is in ANY of the given roles.
    Superusers always pass.
    """
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=roles).exists()