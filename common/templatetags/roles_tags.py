from django import template
from common.roles import user_has_role, ROLE_ADMIN, ROLE_MANAGER, ROLE_EMPLOYEE

register = template.Library()


def _get_user_from_context(context, explicit_user):
    """
    If a user is explicitly passed, use that.
    Otherwise, fall back to context['request'].user.
    """
    if explicit_user is not None:
        return explicit_user

    request = context.get("request")
    if request is not None:
        return getattr(request, "user", None)

    return None


@register.simple_tag(takes_context=True)
def is_admin(context, user=None):
    """
    Usage:
      {% is_admin request.user as is_admin %}
      or simply:
      {% is_admin as is_admin %}     # uses request.user
    """
    user_obj = _get_user_from_context(context, user)
    return bool(user_has_role(user_obj, ROLE_ADMIN))


@register.simple_tag(takes_context=True)
def is_manager(context, user=None):
    """
    Usage:
      {% is_manager request.user as is_manager %}
      or:
      {% is_manager as is_manager %}
    """
    user_obj = _get_user_from_context(context, user)
    return bool(user_has_role(user_obj, ROLE_MANAGER))


@register.simple_tag(takes_context=True)
def is_employee(context, user=None):
    """
    Usage:
      {% is_employee request.user as is_employee %}
      or:
      {% is_employee as is_employee %}
    """
    user_obj = _get_user_from_context(context, user)
    return bool(user_has_role(user_obj, ROLE_EMPLOYEE))


@register.simple_tag(takes_context=True)
def has_role(context, user=None, *roles):
    """
    Generic helper if you ever need it.

    Recommended usage (string roles):
      {% has_role request.user 'admin' 'manager' as can_edit %}

    But for your main pattern, prefer is_admin / is_manager tags.
    """
    # If user looks like a role (string) we shift args
    if user is not None and not hasattr(user, "is_authenticated"):
        roles = (user,) + roles
        user = None

    user_obj = _get_user_from_context(context, user)
    return bool(user_has_role(user_obj, *roles))

