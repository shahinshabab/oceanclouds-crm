# messaging/urls.py

from django.urls import path

from .views import * 

app_name = "messaging"

urlpatterns = [
    # Templates
    path("templates/", EmailTemplateListView.as_view(), name="template_list"),
    path("templates/new/", EmailTemplateCreateView.as_view(), name="template_create"),
    path(
        "templates/<int:pk>/",
        EmailTemplateDetailView.as_view(),
        name="template_detail",
    ),
    path(
        "templates/<int:pk>/edit/",
        EmailTemplateUpdateView.as_view(),
        name="template_update",
    ),
    path(
        "templates/<int:pk>/delete/",
        EmailTemplateDeleteView.as_view(),
        name="template_delete",
    ),
    path("templates/<int:pk>/preview/", EmailTemplatePreviewView.as_view(), name="template_preview"),
    # Campaigns (unchanged from before) ...
    path("campaigns/", CampaignListView.as_view(), name="campaign_list"),
    path("campaigns/new/", CampaignCreateView.as_view(), name="campaign_create"),
    path(
        "campaigns/<int:pk>/",
        CampaignDetailView.as_view(),
        name="campaign_detail",
    ),
    path(
        "campaigns/<int:pk>/edit/",
        CampaignUpdateView.as_view(),
        name="campaign_update",
    ),
    path(
        "campaigns/<int:pk>/delete/",
        CampaignDeleteView.as_view(),
        name="campaign_delete",
    ),
    path(
        "campaigns/<int:pk>/pause/",
        CampaignPauseView.as_view(),
        name="campaign_pause",
    ),
    path(
        "campaigns/<int:pk>/resume/",
        CampaignResumeView.as_view(),
        name="campaign_resume",
    ),
]
