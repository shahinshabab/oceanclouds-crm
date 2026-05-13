from django.db import models
from common.models import TimeStamped
# Create your models here.

# ----------------------------------------------------------------------
# SYSTEM SETTINGS
# ----------------------------------------------------------------------


class SystemSetting(TimeStamped):
    """
    Global system configuration (single-row table in practice).
    """

    site_name = models.CharField(
        max_length=200,
        default="Wedding ERP",
        help_text="Name shown in the header/title of the site.",
    )
    company_name = models.CharField(
        max_length=200,
        default="Ocean Clouds",
        help_text="Your business/legal entity name.",
    )
    default_currency = models.CharField(
        max_length=10,
        default="INR",
        help_text="Default currency code (e.g. AED, INR, USD).",
    )
    timezone = models.CharField(
        max_length=50,
        default="Asia/Kolkata",
        help_text="Default timezone string for the app.",
    )
    support_email = models.EmailField(
        max_length=50,
        default="help@oceanclouds.in",
        help_text="Support or contact email shown to users.",
    )
    allow_self_registration = models.BooleanField(
        default=False,
        help_text="Allow new users to sign up themselves.",
    )

    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"

    def __str__(self):
        return "System Settings"