"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    path("admin-panel/", include("common.urls_admin", namespace="adminpanel")),

    # Landing + Dashboard + Layout
    path("", include("ui.urls")),              

    # CRM (Clients, Contacts, Leads, Inquiries)
    path("crm/", include("crm.urls", namespace="crm")),     

    # Sales (Deals, Proposals, Contracts, Invoices)
    path("sales/", include("sales.urls", namespace="sales")),     

    # Events (Event pages, venues, checklist, calendar)
    path("events/", include("events.urls", namespace="events")),    

    # Services (Packages, service catalog, vendors)
    path("services/", include("services.urls", namespace="services")),

    # Projects (Tasks, deliverables, project management)
    path("projects/", include("projects.urls", namespace="projects")), 

    # Common (tickets, communications, notifications)
    path("common/", include("common.urls", namespace="common")),  
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
