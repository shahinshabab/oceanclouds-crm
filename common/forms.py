# common/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
 
from .models import SystemSetting ,Ticket

User = get_user_model()


class BootstrapModelForm(forms.ModelForm):
    """
    Base form to automatically add Bootstrap classes to widgets.
    - Text / number / email / URL / textarea / date => form-control
    - Select / ModelChoiceField => form-select
    - Checkbox => form-check-input
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():
            widget = field.widget

            # Keep any existing classes
            existing_classes = widget.attrs.get("class", "")

            # Checkbox
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = (existing_classes + " form-check-input").strip()

            # Selects (ChoiceField, ModelChoiceField, etc.)
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                widget.attrs["class"] = (existing_classes + " form-select").strip()

            # Everything else → form-control
            else:
                widget.attrs["class"] = (existing_classes + " form-control").strip()



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

# -------------------------------------------------------------------
# Support Ticket Form
# -------------------------------------------------------------------

class TicketForm(BootstrapModelForm):
    class Meta:
        model = Ticket
        fields = [
            "category",
            "subject_type",
            "subject",
            "description",
            "priority",
            "screenshot",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            # screenshot uses default ClearableFileInput
        }
