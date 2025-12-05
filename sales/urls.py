# sales/urls.py
from django.urls import path

from . import views

app_name = "sales"

urlpatterns = [
    # Deals
    path("deals/", views.DealListView.as_view(), name="deal_list"),
    path("deals/new/", views.DealCreateView.as_view(), name="deal_create"),
    path("deals/<int:pk>/", views.DealDetailView.as_view(), name="deal_detail"),
    path("deals/<int:pk>/edit/", views.DealUpdateView.as_view(), name="deal_update"),

    # Proposals
    path("proposals/", views.ProposalListView.as_view(), name="proposal_list"),
    path("proposals/new/", views.ProposalCreateView.as_view(), name="proposal_create"),
    path("proposals/<int:pk>/", views.ProposalDetailView.as_view(), name="proposal_detail"),
    path("proposals/<int:pk>/edit/", views.ProposalUpdateView.as_view(), name="proposal_update"),

    # Contracts
    path("contracts/", views.ContractListView.as_view(), name="contract_list"),
    path("contracts/new/", views.ContractCreateView.as_view(), name="contract_create"),
    path("contracts/<int:pk>/", views.ContractDetailView.as_view(), name="contract_detail"),
    path("contracts/<int:pk>/edit/", views.ContractUpdateView.as_view(), name="contract_update"),

    # Invoices
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/new/", views.InvoiceCreateView.as_view(), name="invoice_create"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice_update"),
    path("invoices/<int:pk>/download/", views.InvoicePDFDownloadView.as_view(), name="invoice_download"),


    # Payments
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("payments/new/", views.PaymentCreateView.as_view(), name="payment_create"),
    path("payments/<int:pk>/", views.PaymentDetailView.as_view(), name="payment_detail"),
    path("payments/<int:pk>/edit/", views.PaymentUpdateView.as_view(), name="payment_update"),
]
