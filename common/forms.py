# common/forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth.models import Group, Permission
from django.db.models import Q
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



class AnalyticsReportFilterForm(forms.Form):
    REPORT_CRM = "crm"
    REPORT_PERFORMANCE = "performance"

    REPORT_CHOICES = [
        (REPORT_CRM, "CRM Report"),
        (REPORT_PERFORMANCE, "Performance Report"),
    ]

    report_type = forms.ChoiceField(
        choices=REPORT_CHOICES,
        required=True,
        label="Report Type",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_report_type"}),
    )

    # One dropdown for managers + employees
    employee = forms.ModelChoiceField(
        queryset=User.objects.none(),      # set in __init__
        required=False,
        label="Manager / Employee",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_employee"}),
    )

    date_from = forms.DateField(
        required=False,
        label="Date From",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control", "id": "id_date_from"}
        ),
    )

    date_to = forms.DateField(
        required=False,
        label="Date To",
        widget=forms.DateInput(
            attrs={"type": "date", "class": "form-control", "id": "id_date_to"}
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Include ALL managers + employees in the dropdown
        qs = (
            User.objects.filter(
                Q(groups__name="Manager") | Q(groups__name="Employee")
            )
            .distinct()
            .order_by("first_name", "username")
        )
        self.fields["employee"].queryset = qs

        # This is the "All" option (used for CRM only, JS hides it for performance)
        self.fields["employee"].empty_label = "All Managers"

        # Label options as "Name (Manager)" / "Name (Employee)"
        def label_from_instance(user):
            name = user.get_full_name() or user.username
            groups = set(user.groups.values_list("name", flat=True))
            if "Manager" in groups:
                return f"{name} (Manager)"
            elif "Employee" in groups:
                return f"{name} (Employee)"
            return name

        self.fields["employee"].label_from_instance = label_from_instance

