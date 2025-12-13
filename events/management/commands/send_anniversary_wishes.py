from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from messaging.models import EmailTemplate
from messaging.utils import send_templated_email

from events.models import EventPerson
from events.models_anniversary import AnniversaryWishLog  # adjust if you placed it elsewhere


def _get_wedding_date_field(event):
    """
    Adjust this to your actual Event model.
    Common fields: event.date, event.event_date, event.wedding_date
    """
    for attr in ("wedding_date", "event_date", "date"):
        if hasattr(event, attr):
            return getattr(event, attr)
    return None


class Command(BaseCommand):
    help = "Send anniversary wish emails to bride & groom (individually) using ANNIVERSARY template."

    def handle(self, *args, **options):
        today = timezone.localdate()  # uses Django TIME_ZONE (Asia/Dubai in your case)
        current_year = today.year

        # Pull bride/groom people who allow marketing and have emails
        people = (
            EventPerson.objects
            .select_related("event")
            .filter(
                allow_marketing=True,
                email__isnull=False,
            )
            .exclude(email="")
            .filter(role__in=["bride", "groom"])  # if your choices store value differently, adjust this
        )

        sent = 0
        skipped = 0
        failed = 0

        for person in people:
            event = person.event
            wedding_date = _get_wedding_date_field(event)
            if not wedding_date:
                skipped += 1
                continue

            # anniversary match by month/day (ignore year)
            if wedding_date.month != today.month or wedding_date.day != today.day:
                continue

            # avoid duplicates for this year
            if AnniversaryWishLog.objects.filter(person=person, year=current_year).exists():
                skipped += 1
                continue

            # years completed (optional)
            years = current_year - wedding_date.year
            if years <= 0:
                # Same-year wedding: you can decide to skip or still send
                years = 0

            context = {
                "person": person,
                "event": event,
                "client": getattr(event, "client", None),  # if Event has client FK
                "wedding_date": wedding_date,
                "anniversary_years": years,
                "today": today,
            }

            try:
                result = send_templated_email(
                    template_type=EmailTemplate.TemplateType.ANNIVERSARY,
                    to_emails=person.email,
                    context=context,
                )

                if result.ok:
                    AnniversaryWishLog.objects.create(
                        person=person,
                        year=current_year,
                        message_id=result.message_id or "",
                        error="",
                    )
                    sent += 1
                else:
                    AnniversaryWishLog.objects.create(
                        person=person,
                        year=current_year,
                        message_id="",
                        error=result.error or "Unknown error",
                    )
                    failed += 1

            except Exception as e:
                AnniversaryWishLog.objects.create(
                    person=person,
                    year=current_year,
                    message_id="",
                    error=str(e),
                )
                failed += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Anniversary wishes done. sent={sent}, skipped={skipped}, failed={failed}"
            )
        )
