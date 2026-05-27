from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


def make_user(username="tester", password="pass12345", **kwargs):
    defaults = {
        "email": f"{username}@example.com",
        "is_staff": True,
    }
    defaults.update(kwargs)
    return get_user_model().objects.create_user(
        username=username,
        password=password,
        **defaults,
    )


class AuthenticatedViewTestMixin(TestCase):
    list_url_names = []

    @classmethod
    def setUpTestData(cls):
        cls.user = make_user(is_superuser=True)

    def test_list_views_require_login(self):
        for url_name in self.list_url_names:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertIn(response.status_code, [302, 403])
                if response.status_code == 302:
                    self.assertIn(reverse("ui:login"), response["Location"])

    def test_list_views_load_for_authenticated_user(self):
        self.client.force_login(self.user)

        for url_name in self.list_url_names:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 200)
