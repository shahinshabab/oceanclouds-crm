from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils import timezone

from common.test_helpers import AuthenticatedViewTestMixin
from crm.models import Client
from services.models import Service, ServiceDeliverable

from .models import (
    Contract,
    ContractEventDay,
    ContractItem,
    Deal,
    DealStage,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Payment,
    Proposal,
    ProposalEventDay,
    ProposalItem,
    ProposalPlan,
    ProposalStatus,
)


class SalesTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "sales:deal_list",
        "sales:proposal_list",
        "sales:contract_list",
        "sales:invoice_list",
        "sales:payment_list",
    ]

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.client_obj = Client.objects.create(name="Sales Client")
        cls.deal = Deal.objects.create(name="Wedding Deal", client=cls.client_obj)

    def test_proposal_item_defaults_and_recalculates_totals(self):
        service = Service.objects.create(
            name="Wedding Film",
            base_price=Decimal("1500.00"),
        )
        ServiceDeliverable.objects.create(service=service, title="Highlight film")
        proposal = Proposal.objects.create(deal=self.deal, title="Proposal")
        plan = ProposalPlan.objects.create(proposal=proposal, name="Plan", tax_rate=18)
        event_day = ProposalEventDay.objects.create(plan=plan, title="Wedding")

        item = ProposalItem.objects.create(
            event_day=event_day,
            service=service,
            quantity=2,
        )
        plan.refresh_from_db()
        proposal.refresh_from_db()

        self.assertEqual(item.description, service.name)
        self.assertEqual(item.line_total, Decimal("3000.00"))
        self.assertEqual(item.deliverables.count(), 1)
        self.assertEqual(plan.total, Decimal("3540.00"))
        self.assertEqual(proposal.total, Decimal("3540.00"))

    def test_proposal_accept_plan_updates_deal(self):
        proposal = Proposal.objects.create(deal=self.deal, title="Accepted Proposal")
        plan = ProposalPlan.objects.create(
            proposal=proposal,
            name="Accepted Plan",
            total=Decimal("2000.00"),
        )

        proposal.accept_plan(plan)
        self.deal.refresh_from_db()

        self.assertEqual(proposal.status, ProposalStatus.ACCEPTED)
        self.assertEqual(self.deal.stage, DealStage.WON)
        self.assertEqual(self.deal.amount, Decimal("2000.00"))

    def test_proposal_item_requires_service_or_package(self):
        proposal = Proposal.objects.create(deal=self.deal, title="Invalid Proposal")
        plan = ProposalPlan.objects.create(proposal=proposal, name="Plan")
        event_day = ProposalEventDay.objects.create(plan=plan, title="Wedding")

        with self.assertRaises(ValidationError):
            ProposalItem.objects.create(event_day=event_day)

    def test_contract_number_and_signing_token_are_generated(self):
        contract = Contract.objects.create(deal=self.deal)

        self.assertEqual(contract.number, "CTR001")
        self.assertIsNotNone(contract.signing_token)
        self.assertIn(str(contract.signing_token), contract.get_public_sign_path())

    def test_contract_item_recalculates_contract_total(self):
        contract = Contract.objects.create(deal=self.deal)
        event_day = ContractEventDay.objects.create(contract=contract, title="Wedding")

        ContractItem.objects.create(
            contract_event_day=event_day,
            description="Coverage",
            quantity=2,
            unit_price=Decimal("1200.00"),
        )
        contract.refresh_from_db()

        self.assertEqual(contract.total, Decimal("2400.00"))

    def test_invoice_item_and_payment_strings(self):
        invoice = Invoice.objects.create(
            deal=self.deal,
            issue_date=timezone.localdate(),
        )
        item = InvoiceItem.objects.create(
            invoice=invoice,
            description="Advance",
            quantity=1,
            unit_price=Decimal("500.00"),
        )
        invoice.status = InvoiceStatus.ISSUED
        invoice.save()
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("500.00"),
            date=timezone.localdate(),
        )

        self.assertIn("Advance", str(item))
        self.assertIn("500.00", str(payment))
