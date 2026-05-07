# services/models.py

from django.db import models
from django.db.models import Sum
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from common.models import TimeStamped, Owned


# -------------------------------------------------------------------
# Choice enums
# -------------------------------------------------------------------

class ServiceCategory(models.TextChoices):
    PHOTOGRAPHY = "photography", _("Photography")
    VIDEOGRAPHY = "videography", _("Videography")
    DRONE = "drone", _("Drone")
    ALBUM = "album", _("Album / Printing")
    EDITING = "editing", _("Editing / Post Production")
    DECOR = "decor", _("Decor")
    CATERING = "catering", _("Catering")
    MAKEUP = "makeup", _("Makeup & Styling")
    ENTERTAINMENT = "entertainment", _("Entertainment")
    PLANNING = "planning", _("Planning & Coordination")
    VENUE = "venue", _("Venue")
    OTHER = "other", _("Other")


class VendorType(models.TextChoices):
    PHOTOGRAPHER = "photographer", _("Photographer")
    VIDEOGRAPHER = "videographer", _("Videographer")
    DRONE_OPERATOR = "drone_operator", _("Drone Operator")
    EDITOR = "editor", _("Editor")
    ALBUM_VENDOR = "album_vendor", _("Album / Printing Vendor")
    DECOR = "decor", _("Decor Vendor")
    CATERER = "caterer", _("Caterer")
    MAKEUP_ARTIST = "makeup_artist", _("Makeup Artist")
    MUSIC_BAND = "music_band", _("Band / DJ / Entertainment")
    VENUE = "venue", _("Venue Provider")
    OTHER = "other", _("Other")


class InventoryCategory(models.TextChoices):
    CAMERA = "camera", _("Camera")
    LENS = "lens", _("Lens")
    LIGHT = "light", _("Light")
    DRONE = "drone", _("Drone")
    AUDIO = "audio", _("Audio")
    TRIPOD = "tripod", _("Tripod / Stand")
    MEMORY = "memory", _("Memory / Storage")
    COMPUTER = "computer", _("Computer / Editing")
    OTHER = "other", _("Other")


# -------------------------------------------------------------------
# Vendor
# -------------------------------------------------------------------

class Vendor(TimeStamped, Owned):
    """
    External supplier, freelancer, operator, or company resource.

    Examples:
    - Photographer
    - Videographer
    - Drone operator
    - Album printing vendor
    - Decor vendor
    """

    name = models.CharField(
        max_length=255,
        help_text=_("Primary contact, person name, or brand name."),
    )
    company_name = models.CharField(max_length=255, blank=True)

    vendor_type = models.CharField(
        max_length=32,
        choices=VendorType.choices,
        default=VendorType.OTHER,
    )

    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=32, blank=True)
    alt_phone = models.CharField(max_length=32, blank=True)
    whatsapp = models.CharField(max_length=32, blank=True)

    address_line1 = models.CharField(max_length=255, blank=True)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    district = models.CharField(max_length=128, blank=True)
    state = models.CharField(max_length=128, blank=True, default="Kerala")
    country = models.CharField(max_length=128, blank=True, default="India")

    is_preferred = models.BooleanField(
        default=False,
        help_text=_("Mark as preferred / primary vendor."),
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        if self.company_name:
            return f"{self.name} - {self.company_name}"
        return self.name

    def get_absolute_url(self):
        return reverse("services:vendor_detail", args=[self.pk])


# -------------------------------------------------------------------
# Service
# -------------------------------------------------------------------

class Service(TimeStamped, Owned):
    """
    Individual sellable service.

    Examples:
    - Wedding Photography
    - Wedding Videography
    - Drone Coverage
    - Album Designing
    """

    CODE_PREFIX = "SER"
    CODE_PAD = 3

    name = models.CharField(max_length=255)

    code = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        help_text=_("Internal service code. Auto-generated if left blank, e.g., SER001."),
    )

    category = models.CharField(
        max_length=32,
        choices=ServiceCategory.choices,
        default=ServiceCategory.OTHER,
    )

    description = models.TextField(blank=True)

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Base selling price."),
    )

    vendors = models.ManyToManyField(
        Vendor,
        related_name="services",
        blank=True,
        help_text=_("Preferred vendors/operators who can deliver this service."),
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name

    def get_absolute_url(self):
        return reverse("services:service_detail", args=[self.pk])

    @classmethod
    def _generate_next_code(cls):
        prefix = cls.CODE_PREFIX
        pad = cls.CODE_PAD

        last = (
            cls.objects
            .filter(code__startswith=prefix)
            .order_by("-code")
            .only("code")
            .first()
        )

        if last and last.code:
            suffix = last.code.replace(prefix, "")
            try:
                number = int(suffix)
            except ValueError:
                number = 0
        else:
            number = 0

        return f"{prefix}{number + 1:0{pad}d}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_next_code()
        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Package & PackageItem
# -------------------------------------------------------------------

class Package(TimeStamped, Owned):
    """
    Bundle of services.

    Examples:
    - Wedding Base Package
    - Premium Wedding Package
    - Cinematic Wedding Package
    """

    CODE_PREFIX = "PAC"
    CODE_PAD = 3

    name = models.CharField(max_length=255)

    code = models.CharField(
        max_length=64,
        blank=True,
        unique=True,
        help_text=_("Internal package code. Auto-generated if left blank, e.g., PAC001."),
    )

    description = models.TextField(blank=True)

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("Auto-calculated from package items."),
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return f"{self.name} ({self.code})" if self.code else self.name

    def get_absolute_url(self):
        return reverse("services:package_detail", args=[self.pk])

    def recalculate_total(self, save=True):
        total = self.items.aggregate(total=Sum("line_total"))["total"] or 0
        self.total_price = total

        if save:
            self.save(update_fields=["total_price"])

        return total

    @classmethod
    def _generate_next_code(cls):
        prefix = cls.CODE_PREFIX
        pad = cls.CODE_PAD

        last = (
            cls.objects
            .filter(code__startswith=prefix)
            .order_by("-code")
            .only("code")
            .first()
        )

        if last and last.code:
            suffix = last.code.replace(prefix, "")
            try:
                number = int(suffix)
            except ValueError:
                number = 0
        else:
            number = 0

        return f"{prefix}{number + 1:0{pad}d}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self._generate_next_code()
        super().save(*args, **kwargs)


class PackageItem(models.Model):
    """
    Service item inside a package.
    """

    package = models.ForeignKey(
        Package,
        on_delete=models.CASCADE,
        related_name="items",
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="package_items",
        null=True,
        blank=True,
    )

    description = models.CharField(
        max_length=255,
        help_text=_("Visible line description. Example: Wedding Photography - Full Day"),
    )

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    class Meta:
        ordering = ("id",)

    def __str__(self):
        return f"{self.description} x {self.quantity}"

    def save(self, *args, **kwargs):
        if (self.unit_price is None or self.unit_price == 0) and self.service:
            self.unit_price = self.service.base_price or 0

        self.line_total = (self.unit_price or 0) * (self.quantity or 0)

        if not self.description and self.service:
            self.description = self.service.name

        super().save(*args, **kwargs)


# -------------------------------------------------------------------
# Inventory
# -------------------------------------------------------------------

class InventoryItem(TimeStamped, Owned):
    """
    Company physical assets.

    Examples:
    - Camera
    - Lens
    - Light
    - Drone
    - Tripod
    """

    name = models.CharField(max_length=255)

    sku = models.CharField(
        max_length=64,
        blank=True,
        help_text=_("Internal SKU or asset ID."),
    )

    category = models.CharField(
        max_length=32,
        choices=InventoryCategory.choices,
        default=InventoryCategory.OTHER,
    )

    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        related_name="inventory_items",
        null=True,
        blank=True,
        help_text=_("Linked service, if this item is usually used for that service."),
    )

    quantity_total = models.PositiveIntegerField(default=0)
    quantity_available = models.PositiveIntegerField(default=0)

    unit = models.CharField(
        max_length=32,
        default="pcs",
        help_text=_("Example: pcs, sets, units."),
    )

    location = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Storage location."),
    )

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        if self.sku:
            return f"{self.name} ({self.sku})"
        return self.name

    def get_absolute_url(self):
        return reverse("services:inventory_detail", args=[self.pk])