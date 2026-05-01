# common/roles.py

ROLE_ADMIN = "Admin"
ROLE_CRM_MANAGER = "CRM Manager"
ROLE_PROJECT_MANAGER = "Project Manager"
ROLE_EMPLOYEE = "Employee"

# Temporary old role support if you already have "Manager" group
ROLE_MANAGER = "Manager"


CRM_ACCESS_ROLES = [
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
]

SALES_ACCESS_ROLES = [
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
]

PROJECT_ACCESS_ROLES = [
    ROLE_ADMIN,
    ROLE_PROJECT_MANAGER,
]

INQUIRY_ACCESS_ROLES = [
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_PROJECT_MANAGER,
    ROLE_EMPLOYEE,
]

INQUIRY_MANAGE_ROLES = [
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_PROJECT_MANAGER,
]

ROLE_ALL = [
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_PROJECT_MANAGER,
    ROLE_EMPLOYEE,
]


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


def can_access_crm(user):
    return user_has_role(user, *CRM_ACCESS_ROLES)


def can_access_sales(user):
    return user_has_role(user, *SALES_ACCESS_ROLES)


def can_access_project(user):
    return user_has_role(user, *PROJECT_ACCESS_ROLES)


def can_access_inquiry(user):
    return user_has_role(user, *INQUIRY_ACCESS_ROLES)


def can_manage_inquiry(user):
    return user_has_role(user, *INQUIRY_MANAGE_ROLES)