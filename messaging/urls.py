# messaging/urls.py

from django.urls import path

from .views import (
    EmailTemplateListView,
    EmailTemplateCreateView,
    EmailTemplateDetailView,
    EmailTemplateUpdateView,
    EmailTemplateDeleteView,
    EmailTemplatePreviewView,

    WhatsAppTemplateListView,
    WhatsAppTemplateCreateView,
    WhatsAppTemplateDetailView,
    WhatsAppTemplateUpdateView,
    WhatsAppTemplateDeleteView,
    WhatsAppTemplatePreviewView,
    WhatsAppSendLogListView,

    CampaignListView,
    CampaignCreateView,
    CampaignDetailView,
    CampaignUpdateView,
    CampaignDeleteView,
    CampaignPauseView,
    CampaignResumeView,
    EmailSendLogListView,

    TicketCreateView,
    TicketListView,
    TicketDetailView
)

app_name = "messaging"

urlpatterns = [
    # Email Templates
    path("templates/", EmailTemplateListView.as_view(), name="template_list"),
    path("templates/new/", EmailTemplateCreateView.as_view(), name="template_create"),
    path("templates/<int:pk>/", EmailTemplateDetailView.as_view(), name="template_detail"),
    path("templates/<int:pk>/edit/", EmailTemplateUpdateView.as_view(), name="template_update"),
    path("templates/<int:pk>/delete/", EmailTemplateDeleteView.as_view(), name="template_delete"),
    path("templates/<int:pk>/preview/", EmailTemplatePreviewView.as_view(), name="template_preview"),

    # WhatsApp Templates
    path("whatsapp/templates/", WhatsAppTemplateListView.as_view(), name="whatsapp_template_list"),
    path("whatsapp/templates/new/", WhatsAppTemplateCreateView.as_view(), name="whatsapp_template_create"),
    path("whatsapp/templates/<int:pk>/", WhatsAppTemplateDetailView.as_view(), name="whatsapp_template_detail"),
    path("whatsapp/templates/<int:pk>/edit/", WhatsAppTemplateUpdateView.as_view(), name="whatsapp_template_update"),
    path("whatsapp/templates/<int:pk>/delete/", WhatsAppTemplateDeleteView.as_view(), name="whatsapp_template_delete"),
    path("whatsapp/templates/<int:pk>/preview/", WhatsAppTemplatePreviewView.as_view(), name="whatsapp_template_preview"),

    # Campaigns
    path("campaigns/", CampaignListView.as_view(), name="campaign_list"),
    path("campaigns/new/", CampaignCreateView.as_view(), name="campaign_create"),
    path("campaigns/<int:pk>/", CampaignDetailView.as_view(), name="campaign_detail"),
    path("campaigns/<int:pk>/edit/", CampaignUpdateView.as_view(), name="campaign_update"),
    path("campaigns/<int:pk>/delete/", CampaignDeleteView.as_view(), name="campaign_delete"),
    path("campaigns/<int:pk>/pause/", CampaignPauseView.as_view(), name="campaign_pause"),
    path("campaigns/<int:pk>/resume/", CampaignResumeView.as_view(), name="campaign_resume"),

    # Logs
    path("logs/", EmailSendLogListView.as_view(), name="email_log_list"),
    path("whatsapp/logs/", WhatsAppSendLogListView.as_view(), name="whatsapp_log_list"),

    path("tickets/", TicketListView.as_view(), name="ticket_list"),
    path("tickets/new/", TicketCreateView.as_view(), name="ticket_create"),
    path("tickets/<int:pk>/", TicketDetailView.as_view(), name="ticket_detail"),
]