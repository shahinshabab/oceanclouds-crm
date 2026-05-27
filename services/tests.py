from decimal import Decimal

from common.test_helpers import AuthenticatedViewTestMixin

from .forms import InventoryItemForm
from .models import (
    InventoryItem,
    Package,
    PackageDeliverable,
    PackageItem,
    Service,
    ServiceDeliverable,
    Vendor,
)


class ServicesTests(AuthenticatedViewTestMixin):
    list_url_names = [
        "services:vendor_list",
        "services:service_list",
        "services:package_list",
        "services:inventory_list",
    ]

    def test_vendor_string_prefers_company_when_available(self):
        vendor = Vendor.objects.create(name="Anu", company_name="Ocean Studio")

        self.assertEqual(str(vendor), "Anu - Ocean Studio")

    def test_service_auto_generates_code_and_preserves_it(self):
        service = Service.objects.create(
            name="Wedding Photography",
            base_price=Decimal("1000.00"),
        )

        self.assertRegex(service.code, r"^SER\d{3}$")
        service.name = "Wedding Photo"
        service.save()
        self.assertRegex(service.code, r"^SER\d{3}$")

    def test_package_item_updates_package_total(self):
        service = Service.objects.create(
            name="Cinematic Film",
            base_price=Decimal("2500.00"),
        )
        package = Package.objects.create(name="Premium")

        item = PackageItem.objects.create(package=package, service=service, quantity=2)
        package.refresh_from_db()

        self.assertEqual(item.description, service.name)
        self.assertEqual(item.line_total, Decimal("5000.00"))
        self.assertEqual(package.total_price, Decimal("5000.00"))

    def test_default_deliverable_strings(self):
        service = Service.objects.create(name="Album", base_price=Decimal("500.00"))
        package = Package.objects.create(name="Album Pack")

        service_deliverable = ServiceDeliverable.objects.create(
            service=service,
            title="Edited photos",
        )
        package_deliverable = PackageDeliverable.objects.create(
            package=package,
            title="Online gallery",
        )

        self.assertEqual(str(service_deliverable), "Album - Edited photos")
        self.assertEqual(str(package_deliverable), "Album Pack - Online gallery")

    def test_inventory_form_rejects_available_more_than_total(self):
        form = InventoryItemForm(
            data={
                "name": "Camera",
                "sku": "CAM-1",
                "category": "camera",
                "service": "",
                "quantity_total": 1,
                "quantity_available": 2,
                "unit": "pcs",
                "location": "",
                "is_active": "on",
                "notes": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("quantity_available", form.errors)

    def test_inventory_string_uses_sku_when_present(self):
        item = InventoryItem.objects.create(name="Lens", sku="L-1")

        self.assertEqual(str(item), "Lens (L-1)")
