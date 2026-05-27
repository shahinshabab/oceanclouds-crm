from django.urls import reverse

from common.test_helpers import AuthenticatedViewTestMixin, make_user

from .forms import ProfileUpdateForm


class UiTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "ui:home",
        "ui:profile",
        "ui:profile_edit",
        "ui:profile_password",
    ]

    def test_login_page_loads(self):
        response = self.client.get(reverse("ui:login"))

        self.assertEqual(response.status_code, 200)

    def test_login_with_valid_credentials_redirects_home(self):
        user = make_user(username="login-user", password="secret12345")

        response = self.client.post(
            reverse("ui:login"),
            data={"username": user.username, "password": "secret12345"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("ui:home"))

    def test_profile_form_updates_user_fields(self):
        form = ProfileUpdateForm(
            data={
                "first_name": "Ocean",
                "last_name": "User",
                "email": "ocean@example.com",
            },
            instance=self.user,
        )

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.email, "ocean@example.com")
