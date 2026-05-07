# services/urls.py

from django.urls import path

from . import views

app_name = "services"

urlpatterns = [
    # Vendors
    path("vendors/", views.VendorListView.as_view(), name="vendor_list"),
    path("vendors/new/", views.VendorCreateView.as_view(), name="vendor_create"),
    path("vendors/<int:pk>/", views.VendorDetailView.as_view(), name="vendor_detail"),
    path("vendors/<int:pk>/edit/", views.VendorUpdateView.as_view(), name="vendor_update"),
    path("vendors/<int:pk>/delete/", views.VendorDeleteView.as_view(), name="vendor_delete"),

    # Services
    path("services/", views.ServiceListView.as_view(), name="service_list"),
    path("services/new/", views.ServiceCreateView.as_view(), name="service_create"),
    path("services/<int:pk>/", views.ServiceDetailView.as_view(), name="service_detail"),
    path("services/<int:pk>/edit/", views.ServiceUpdateView.as_view(), name="service_update"),
    path("services/<int:pk>/delete/", views.ServiceDeleteView.as_view(), name="service_delete"),

    # Packages
    path("packages/", views.PackageListView.as_view(), name="package_list"),
    path("packages/new/", views.PackageCreateView.as_view(), name="package_create"),
    path("packages/<int:pk>/", views.PackageDetailView.as_view(), name="package_detail"),
    path("packages/<int:pk>/edit/", views.PackageUpdateView.as_view(), name="package_update"),
    path("packages/<int:pk>/delete/", views.PackageDeleteView.as_view(), name="package_delete"),

    # Inventory
    path("inventory/", views.InventoryItemListView.as_view(), name="inventory_list"),
    path("inventory/new/", views.InventoryItemCreateView.as_view(), name="inventory_create"),
    path("inventory/<int:pk>/", views.InventoryItemDetailView.as_view(), name="inventory_detail"),
    path("inventory/<int:pk>/edit/", views.InventoryItemUpdateView.as_view(), name="inventory_update"),
    path("inventory/<int:pk>/delete/", views.InventoryItemDeleteView.as_view(), name="inventory_delete"),
]