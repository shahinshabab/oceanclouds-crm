from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    # Clients
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/new/", views.ClientCreateView.as_view(), name="client_create"),
    path("clients/<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path("clients/<int:pk>/edit/", views.ClientUpdateView.as_view(), name="client_update"),

    # Contacts
    path("contacts/", views.ContactListView.as_view(), name="contact_list"),
    path("contacts/new/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<int:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_update"),

    # Leads
    path("leads/", views.LeadListView.as_view(), name="lead_list"),
    path("leads/new/", views.LeadCreateView.as_view(), name="lead_create"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<int:pk>/edit/", views.LeadUpdateView.as_view(), name="lead_update"),

    # Inquiries
    path("inquiries/", views.InquiryListView.as_view(), name="inquiry_list"),
    path("inquiries/new/", views.InquiryCreateView.as_view(), name="inquiry_create"),
    path("inquiries/<int:pk>/", views.InquiryDetailView.as_view(), name="inquiry_detail"),
    path("inquiries/<int:pk>/edit/", views.InquiryUpdateView.as_view(), name="inquiry_update"),

    # reviews
    path("reviews/", views.ClientReviewListView.as_view(), name="review_list"),
    path("reviews/<int:pk>/", views.ClientReviewDetailView.as_view(), name="review_detail"),
    path("reviews/add/", views.ClientReviewCreateView.as_view(), name="review_create"),
    path("reviews/<int:pk>/edit/", views.ClientReviewUpdateView.as_view(), name="review_update"),
]
