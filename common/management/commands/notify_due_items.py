# common/management/commands/notify_due_items.py

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from common.models import Notification
from common.notifications import notify_user


class Command(BaseCommand):
    help = "Create due-date notifications for CRM, Sales and Project records."

    def handle(self, *args, **options):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        self.notify_crm(today, tomorrow)
        self.notify_sales(today, tomorrow)
        self.notify_projects(today, tomorrow)

        self.stdout.write(self.style.SUCCESS("Due notification check completed."))

    def notify_crm(self, today, tomorrow):
        from crm.models import Lead

        # Change this list if your Lead model uses a different follow-up field name.
        possible_fields = ["follow_up_date", "next_follow_up_date", "next_action_date"]
        field_name = self._first_existing_field(Lead, possible_fields)

        if not field_name:
            return

        filter_kwargs = {
            f"{field_name}__in": [today, tomorrow],
        }

        leads = Lead.objects.select_related("owner").filter(**filter_kwargs)

        for lead in leads:
            recipient = getattr(lead, "owner", None)
            due_date = getattr(lead, field_name, None)

            if not recipient or not due_date:
                continue

            notify_user(
                recipient=recipient,
                notif_type=Notification.Type.LEAD_FOLLOW_UP,
                target=lead,
                message=f"Lead follow-up due: {lead}",
                extra_key=str(due_date),
            )

    def notify_sales(self, today, tomorrow):
        from sales.models import Deal, Proposal, Contract, Invoice

        # Deal expected close
        if self._has_field(Deal, "expected_close_date"):
            deals = Deal.objects.select_related("owner").filter(
                expected_close_date__in=[today, tomorrow],
                is_active=True,
            )

            for deal in deals:
                if deal.owner_id:
                    notify_user(
                        recipient=deal.owner,
                        notif_type=Notification.Type.DEAL_EXPECTED_CLOSE,
                        target=deal,
                        message=f"Deal expected close date is near: {deal}",
                        extra_key=str(deal.expected_close_date),
                    )

        # Proposal due
        proposal_due_field = self._first_existing_field(
            Proposal,
            ["due_date", "valid_until", "expiry_date"],
        )

        if proposal_due_field:
            filter_kwargs = {
                f"{proposal_due_field}__in": [today, tomorrow],
            }

            proposals = Proposal.objects.select_related("owner", "deal", "deal__owner").filter(
                **filter_kwargs
            )

            for proposal in proposals:
                recipient = getattr(proposal, "owner", None)

                if not recipient and getattr(proposal, "deal", None):
                    recipient = getattr(proposal.deal, "owner", None)

                due_date = getattr(proposal, proposal_due_field, None)

                if recipient and due_date:
                    notify_user(
                        recipient=recipient,
                        notif_type=Notification.Type.PROPOSAL_DUE,
                        target=proposal,
                        message=f"Proposal due date is near: {proposal}",
                        extra_key=str(due_date),
                    )

        # Contract end
        contract_end_field = self._first_existing_field(
            Contract,
            ["end_date", "valid_until", "expiry_date"],
        )

        if contract_end_field:
            filter_kwargs = {
                f"{contract_end_field}__in": [today, tomorrow],
            }

            contracts = Contract.objects.select_related("owner", "deal", "deal__owner").filter(
                **filter_kwargs
            )

            for contract in contracts:
                recipient = getattr(contract, "owner", None)

                if not recipient and getattr(contract, "deal", None):
                    recipient = getattr(contract.deal, "owner", None)

                end_date = getattr(contract, contract_end_field, None)

                if recipient and end_date:
                    notify_user(
                        recipient=recipient,
                        notif_type=Notification.Type.CONTRACT_ENDING,
                        target=contract,
                        message=f"Contract end date is near: {contract}",
                        extra_key=str(end_date),
                    )

        # Invoice due
        if self._has_field(Invoice, "due_date"):
            invoices = Invoice.objects.select_related("owner", "deal", "deal__owner").filter(
                due_date__in=[today, tomorrow],
            )

            for invoice in invoices:
                recipient = getattr(invoice, "owner", None)

                if not recipient and getattr(invoice, "deal", None):
                    recipient = getattr(invoice.deal, "owner", None)

                if recipient and invoice.due_date:
                    notify_user(
                        recipient=recipient,
                        notif_type=Notification.Type.INVOICE_DUE,
                        target=invoice,
                        message=f"Invoice due date is near: {invoice}",
                        extra_key=str(invoice.due_date),
                    )

    def notify_projects(self, today, tomorrow):
        from projects.models import (
            Project,
            Task,
            Deliverable,
            ProjectStatus,
            TaskStatus,
            DeliverableStatus,
        )

        # Project due
        if self._has_field(Project, "due_date"):
            projects = Project.objects.select_related("manager").filter(
                due_date__in=[today, tomorrow],
            ).exclude(status=ProjectStatus.COMPLETED)

            for project in projects:
                if project.manager_id:
                    notify_user(
                        recipient=project.manager,
                        notif_type=Notification.Type.PROJECT_DUE,
                        target=project,
                        message=f"Project due date is near: {project.name}",
                        extra_key=str(project.due_date),
                    )

        # Task due
        if self._has_field(Task, "due_date"):
            tasks = Task.objects.select_related("assigned_to", "project").filter(
                due_date__in=[today, tomorrow],
            ).exclude(status=TaskStatus.COMPLETED)

            for task in tasks:
                if task.assigned_to_id:
                    notify_user(
                        recipient=task.assigned_to,
                        notif_type=Notification.Type.TASK_DUE,
                        target=task,
                        message=f"Task due date is near: {task.name}",
                        extra_key=str(task.due_date),
                    )

        # Deliverable due
        if self._has_field(Deliverable, "due_date"):
            deliverables = Deliverable.objects.select_related("assigned_to", "project").filter(
                due_date__in=[today, tomorrow],
            ).exclude(status=DeliverableStatus.DELIVERED)

            for deliverable in deliverables:
                if deliverable.assigned_to_id:
                    notify_user(
                        recipient=deliverable.assigned_to,
                        notif_type=Notification.Type.DELIVERABLE_DUE,
                        target=deliverable,
                        message=f"Deliverable due date is near: {deliverable.name}",
                        extra_key=str(deliverable.due_date),
                    )

    def _has_field(self, model, field_name):
        return any(field.name == field_name for field in model._meta.get_fields())

    def _first_existing_field(self, model, field_names):
        for field_name in field_names:
            if self._has_field(model, field_name):
                return field_name
        return None