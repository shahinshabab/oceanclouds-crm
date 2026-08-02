from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.test import Client
from django.urls import reverse


class Command(BaseCommand):
    help = "Run read-only authenticated smoke checks against important workflows."

    workflow_urls = [
        "ui:home",
        "ui:profile",
        "crm:client_list",
        "crm:contact_list",
        "crm:lead_list",
        "crm:inquiry_list",
        "sales:deal_list",
        "sales:proposal_list",
        "sales:contract_list",
        "sales:invoice_list",
        "projects:project_list",
        "projects:task_list",
        "projects:deliverable_list",
        "reports:dashboard",
        "reports:sales_report",
        "reports:project_report",
        "reports:employee_work_report",
    ]

    def handle(self, *args, **options):
        user_model = get_user_model()
        user = (
            user_model._base_manager.filter(
                is_active=True,
                is_staff=True,
            )
            .order_by("pk")
            .first()
        )
        if user is None:
            raise CommandError("No active staff user is available for smoke checks.")
        if not user.has_usable_password():
            raise CommandError("The selected active staff user has no usable password hash.")

        client = Client(HTTP_HOST="localhost")
        login_response = client.get(reverse("ui:login"), secure=True)
        if login_response.status_code != 200:
            raise CommandError(
                f"Login page returned HTTP {login_response.status_code}."
            )

        failures = []
        with transaction.atomic():
            client.force_login(user)
            for url_name in self.workflow_urls:
                response = client.get(reverse(url_name), secure=True)
                if response.status_code != 200:
                    failures.append(f"{url_name}=HTTP {response.status_code}")
            transaction.set_rollback(True)

        if failures:
            raise CommandError("Workflow smoke checks failed: " + ", ".join(failures))

        self.stdout.write(
            self.style.SUCCESS(
                f"Deployment smoke checks passed: database={connection.vendor}, "
                f"login_page=200, authenticated_workflows={len(self.workflow_urls)}."
            )
        )
