# messaging/urls.py
from django.urls import path

from .views import (
    MessageTemplateListView,
    MessageTemplateDetailView,
    MessageTemplateCreateView,
    MessageTemplateUpdateView,
    CampaignListView,
    CampaignDetailView,
    CampaignCreateView,
    CampaignUpdateView,
    campaign_send_now,
    EmailIntegrationSettingsView,
)

app_name = "messaging"

urlpatterns = [
    # Templates
    path("templates/", MessageTemplateListView.as_view(), name="template_list"),
    path("templates/new/", MessageTemplateCreateView.as_view(), name="template_create"),
    path("templates/<int:pk>/", MessageTemplateDetailView.as_view(), name="template_detail"),
    path("templates/<int:pk>/edit/", MessageTemplateUpdateView.as_view(), name="template_update"),

    # Campaigns
    path("campaigns/", CampaignListView.as_view(), name="campaign_list"),
    path("campaigns/new/", CampaignCreateView.as_view(), name="campaign_create"),
    path("campaigns/<int:pk>/", CampaignDetailView.as_view(), name="campaign_detail"),
    path("campaigns/<int:pk>/edit/", CampaignUpdateView.as_view(), name="campaign_update"),
    path("campaigns/<int:pk>/send/", campaign_send_now, name="campaign_send_now"),
    path(
        "settings/integration/",
        EmailIntegrationSettingsView.as_view(),
        name="integration_settings",
    ),
]
