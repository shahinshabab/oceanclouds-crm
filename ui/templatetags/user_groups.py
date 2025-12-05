# ui/templatetags/user_groups.py
from django import template

register = template.Library()

@register.filter
def has_group(user, group_name):
    """
    Usage in template:
        {% if user|has_group:"Admin" %}
    """
    if not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()
