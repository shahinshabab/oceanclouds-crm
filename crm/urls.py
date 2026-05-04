# crm/urls.py
from django.urls import path
from . import views

app_name = "crm"

urlpatterns = [
    path("clients/", views.ClientListView.as_view(), name="client_list"),
    path("clients/new/", views.ClientCreateView.as_view(), name="client_create"),
    path("clients/<int:pk>/", views.ClientDetailView.as_view(), name="client_detail"),
    path("clients/<int:pk>/edit/", views.ClientUpdateView.as_view(), name="client_update"),
    path("clients/<int:pk>/delete/", views.ClientDeleteView.as_view(), name="client_delete"),

    path("contacts/", views.ContactListView.as_view(), name="contact_list"),
    path("contacts/new/", views.ContactCreateView.as_view(), name="contact_create"),
    path("contacts/<int:pk>/", views.ContactDetailView.as_view(), name="contact_detail"),
    path("contacts/<int:pk>/edit/", views.ContactUpdateView.as_view(), name="contact_update"),
    path("contacts/<int:pk>/delete/", views.ContactDeleteView.as_view(), name="contact_delete"),

    path("leads/", views.LeadListView.as_view(), name="lead_list"),
    path("leads/new/", views.LeadCreateView.as_view(), name="lead_create"),
    path("leads/<int:pk>/", views.LeadDetailView.as_view(), name="lead_detail"),
    path("leads/<int:pk>/edit/", views.LeadUpdateView.as_view(), name="lead_update"),
    path("leads/<int:pk>/delete/", views.LeadDeleteView.as_view(), name="lead_delete"),

    path("inquiries/", views.InquiryListView.as_view(), name="inquiry_list"),
    path("inquiries/new/", views.InquiryCreateView.as_view(), name="inquiry_create"),
    path("inquiries/<int:pk>/", views.InquiryDetailView.as_view(), name="inquiry_detail"),
    path("inquiries/<int:pk>/edit/", views.InquiryUpdateView.as_view(), name="inquiry_update"),
    path("inquiries/<int:pk>/delete/", views.InquiryDeleteView.as_view(), name="inquiry_delete"),
    path("inquiries/<int:pk>/convert-to-lead/", views.InquiryConvertToLeadView.as_view(), name="inquiry_convert_to_lead"),

    path("reviews/", views.ReviewListView.as_view(), name="review_list"),
    path("reviews/add/", views.ReviewCreateView.as_view(), name="review_create"),
    path("reviews/<int:pk>/", views.ReviewDetailView.as_view(), name="review_detail"),
    path("reviews/<int:pk>/edit/", views.ReviewUpdateView.as_view(), name="review_update"),
    path("reviews/<int:pk>/delete/", views.ReviewDeleteView.as_view(), name="review_delete"),
]
