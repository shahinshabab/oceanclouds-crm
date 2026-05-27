from django.contrib.auth.models import Group
from django.urls import reverse

from common.test_helpers import AuthenticatedViewTestMixin

from .forms import RoleForm, SystemSettingForm
from .models import SystemSetting


class AdminPanelModelAndFormTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "adminpanel:user_list",
        "adminpanel:role_list",
        "adminpanel:system_settings",
    ]

    def test_system_setting_string_and_defaults(self):
        setting = SystemSetting.objects.create()

        self.assertEqual(str(setting), "System Settings")
        self.assertEqual(setting.company_name, "Ocean Clouds")
        self.assertEqual(setting.default_currency, "INR")

    def test_system_setting_form_accepts_valid_data(self):
        form = SystemSettingForm(
            data={
                "site_name": "Ocean CRM",
                "company_name": "Ocean Clouds",
                "default_currency": "INR",
                "timezone": "Asia/Kolkata",
                "support_email": "help@example.com",
                "allow_self_registration": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)

    def test_role_form_creates_group(self):
        form = RoleForm(data={"name": "CRM Manager", "permissions": []})

        self.assertTrue(form.is_valid(), form.errors)
        group = form.save()
        self.assertEqual(group, Group.objects.get(name="CRM Manager"))

    def test_edit_urls_reverse(self):
        group = Group.objects.create(name="Editors")

        self.assertEqual(
            reverse("adminpanel:role_edit", args=[group.pk]),
            f"/adminpanel/roles/{group.pk}/edit/",
        )
