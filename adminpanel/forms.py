from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission

from common.models import SystemSetting


User = get_user_model()


class BootstrapFormMixin:
    """
    Adds Bootstrap classes to all form fields.
    Works with ModelForm, UserCreationForm, UserChangeForm, etc.
    """

    def apply_bootstrap_classes(self):
        for field in self.fields.values():
            widget = field.widget
            existing = widget.attrs.get("class", "")

            if isinstance(widget, forms.CheckboxInput):
                css_class = "form-check-input"
            elif isinstance(widget, forms.CheckboxSelectMultiple):
                css_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                css_class = "form-select"
            else:
                css_class = "form-control"

            widget.attrs["class"] = f"{existing} {css_class}".strip()


class UserCreateForm(BootstrapFormMixin, UserCreationForm):
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["groups"].queryset = Group.objects.all().order_by("name")
        self.fields["groups"].required = False
        self.fields["groups"].widget.attrs.update({"class": "form-select"})

        self.apply_bootstrap_classes()


class UserUpdateForm(BootstrapFormMixin, UserChangeForm):
    password = None

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["groups"].queryset = Group.objects.all().order_by("name")
        self.fields["groups"].required = False
        self.fields["groups"].widget.attrs.update({"class": "form-select"})

        self.apply_bootstrap_classes()


class RoleForm(BootstrapFormMixin, forms.ModelForm):
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.select_related("content_type").order_by(
            "content_type__app_label",
            "content_type__model",
            "codename",
        ),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = Group
        fields = ("name", "permissions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["name"].widget.attrs.update({
            "placeholder": "Example: CRM Manager",
        })

        self.apply_bootstrap_classes()


class SystemSettingForm(BootstrapFormMixin, forms.ModelForm):
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

        widgets = {
            "site_name": forms.TextInput(attrs={
                "placeholder": "Wedding CRM",
            }),
            "company_name": forms.TextInput(attrs={
                "placeholder": "Ocean Clouds",
            }),
            "default_currency": forms.TextInput(attrs={
                "placeholder": "INR",
            }),
            "timezone": forms.TextInput(attrs={
                "placeholder": "Asia/Kolkata",
            }),
            "support_email": forms.EmailInput(attrs={
                "placeholder": "help@oceanclouds.in",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_bootstrap_classes()