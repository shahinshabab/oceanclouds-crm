# common/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
from .models import SystemSetting 

User = get_user_model()


from django import forms

class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                cls = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                cls = "form-select"
            else:
                cls = "form-control"

            widget.attrs["class"] = f"{existing} {cls}".strip()



class UserCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
        )


class UserUpdateForm(UserChangeForm):
    password = None  # hide password field

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
        )


class RoleForm(forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all().order_by(
            "content_type__app_label", "codename"
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Group
        fields = ("name", "permissions")


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSetting
        fields = [
            "site_name",
            "company_name",
            "default_currency",
            "timezone",
            "support_email",
            "allow_self_registration",
        ]
