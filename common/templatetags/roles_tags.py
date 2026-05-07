# common/templatetags/roles_tags.py

from django import template

from common.roles import (
    ROLE_ADMIN,
    ROLE_CRM_MANAGER,
    ROLE_PROJECT_MANAGER,
    ROLE_EMPLOYEE,
    ROLE_MANAGER,
    can_access_crm,
    can_access_sales,
    can_access_project,
    can_access_project_work,
    can_access_inquiry,
    can_manage_inquiry,
    can_manage_services,
    can_manage_events,
    can_access_event_calendar,
    user_has_role,
)

register = template.Library()


@register.simple_tag
def is_admin(user):
    return user_has_role(user, ROLE_ADMIN)


@register.simple_tag
def is_crm_manager(user):
    return user_has_role(user, ROLE_CRM_MANAGER)


@register.simple_tag
def is_project_manager(user):
    return user_has_role(user, ROLE_PROJECT_MANAGER)


@register.simple_tag
def is_employee(user):
    return user_has_role(user, ROLE_EMPLOYEE)


@register.simple_tag
def has_crm_access(user):
    return can_access_crm(user)


@register.simple_tag
def has_sales_access(user):
    return can_access_sales(user)


@register.simple_tag
def has_project_access(user):
    return can_access_project(user)


@register.simple_tag
def has_project_work_access(user):
    return can_access_project_work(user)


@register.simple_tag
def has_inquiry_access(user):
    return can_access_inquiry(user)


@register.simple_tag
def has_inquiry_manage_access(user):
    return can_manage_inquiry(user)


@register.simple_tag
def has_services_manage_access(user):
    """
    Services master data:
    Admin only.
    """
    return can_manage_services(user)


# Keep temporarily for old templates
@register.simple_tag
def is_manager(user):
    return user_has_role(
        user,
        ROLE_MANAGER,
        ROLE_CRM_MANAGER,
        ROLE_PROJECT_MANAGER,
    )


@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.simple_tag
def has_event_manage_access(user):
    return can_manage_events(user)


@register.simple_tag
def has_event_calendar_access(user):
    return can_access_event_calendar(user)