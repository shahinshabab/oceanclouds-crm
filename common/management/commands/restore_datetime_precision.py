import sqlite3
from datetime import timezone as datetime_timezone
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.db.models import DateField, DateTimeField
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime


def quote_sqlite_identifier(value):
    return f'"{value.replace(chr(34), chr(34) * 2)}"'


class Command(BaseCommand):
    help = "Restore sub-millisecond date precision from a source SQLite database."

    def add_arguments(self, parser):
        parser.add_argument("--sqlite", required=True)

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            raise CommandError("The target/default database must be PostgreSQL.")

        sqlite_path = Path(options["sqlite"])
        if not sqlite_path.is_file():
            raise CommandError(f"SQLite source not found: {sqlite_path}")

        source = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
        source.row_factory = sqlite3.Row
        user_model = get_user_model()
        updated = 0
        missing = []

        try:
            with transaction.atomic():
                for model in sorted(
                    apps.get_models(), key=lambda item: item._meta.label_lower
                ):
                    if model._meta.proxy or not model._meta.managed:
                        continue

                    date_fields = [
                        field
                        for field in model._meta.fields
                        if isinstance(field, DateField)
                    ]
                    if not date_fields:
                        continue

                    if model is user_model:
                        lookup_field = user_model.USERNAME_FIELD
                        source_lookup_column = model._meta.get_field(
                            lookup_field
                        ).column
                    else:
                        lookup_field = model._meta.pk.name
                        source_lookup_column = model._meta.pk.column

                    selected_columns = [source_lookup_column] + [
                        field.column for field in date_fields
                    ]
                    sql = "SELECT {} FROM {}".format(
                        ", ".join(
                            quote_sqlite_identifier(column)
                            for column in selected_columns
                        ),
                        quote_sqlite_identifier(model._meta.db_table),
                    )

                    try:
                        rows = source.execute(sql)
                    except sqlite3.OperationalError as error:
                        raise CommandError(
                            f"Could not read {model._meta.label}: {error}"
                        ) from error

                    for row in rows:
                        values = {}
                        for field in date_fields:
                            raw_value = row[field.column]
                            if raw_value is None:
                                values[field.name] = None
                            elif isinstance(field, DateTimeField):
                                parsed = parse_datetime(raw_value)
                                if parsed is None:
                                    raise CommandError(
                                        f"Invalid datetime in {model._meta.label}.{field.name}"
                                    )
                                if timezone.is_naive(parsed) and settings.USE_TZ:
                                    parsed = timezone.make_aware(
                                        parsed, datetime_timezone.utc
                                    )
                                values[field.name] = parsed
                            else:
                                parsed = parse_date(raw_value)
                                if parsed is None:
                                    raise CommandError(
                                        f"Invalid date in {model._meta.label}.{field.name}"
                                    )
                                values[field.name] = parsed

                        matched = model._base_manager.filter(
                            **{lookup_field: row[source_lookup_column]}
                        ).update(**values)
                        if matched != 1:
                            missing.append(
                                f"{model._meta.label}:{row[source_lookup_column]}"
                            )
                        updated += matched
        finally:
            source.close()

        if missing:
            raise CommandError(
                f"Could not match {len(missing)} source rows in PostgreSQL."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Restored exact date/time values on {updated} PostgreSQL rows."
            )
        )
