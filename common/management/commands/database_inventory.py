import json
import hashlib
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import DateField, FileField, Max, Min


def serialize_datetime(value):
    return value.isoformat() if value is not None else None


def fingerprint(value):
    payload = json.dumps(
        value,
        default=str,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def object_identity(instance):
    natural_key = getattr(instance, "natural_key", None)
    return natural_key() if callable(natural_key) else str(instance.pk)


class Command(BaseCommand):
    help = "Write a privacy-safe database inventory for migration verification."

    def add_arguments(self, parser):
        parser.add_argument("--output", required=True)

    def handle(self, *args, **options):
        inventory = {
            "database_vendor": connection.vendor,
            "models": {},
            "users": {},
            "permissions": {},
            "date_fields": {},
            "file_fields": {},
        }

        for model in sorted(apps.get_models(), key=lambda item: item._meta.label_lower):
            if model._meta.proxy or not model._meta.managed:
                continue

            label = model._meta.label
            manager = model._base_manager
            inventory["models"][label] = manager.count()

            for field in model._meta.fields:
                field_label = f"{label}.{field.name}"

                if isinstance(field, DateField):
                    bounds = manager.aggregate(
                        minimum=Min(field.name),
                        maximum=Max(field.name),
                    )
                    inventory["date_fields"][field_label] = {
                        "non_null": manager.filter(
                            **{f"{field.name}__isnull": False}
                        ).count(),
                        "minimum": serialize_datetime(bounds["minimum"]),
                        "maximum": serialize_datetime(bounds["maximum"]),
                        "fingerprint": fingerprint(
                            sorted(
                                (
                                    object_identity(item),
                                    serialize_datetime(getattr(item, field.name)),
                                )
                                for item in manager.exclude(
                                    **{f"{field.name}__isnull": True}
                                ).only("pk", field.name)
                            )
                        ),
                    }

                if isinstance(field, FileField):
                    values = list(
                        manager.exclude(**{field.name: ""})
                        .exclude(**{f"{field.name}__isnull": True})
                        .values_list(field.name, flat=True)
                    )
                    existing = sum(
                        (Path(settings.MEDIA_ROOT) / value).is_file()
                        for value in values
                    )
                    inventory["file_fields"][field_label] = {
                        "references": len(values),
                        "files_found": existing,
                        "files_missing": len(values) - existing,
                        "reference_fingerprint": fingerprint(sorted(values)),
                    }

        user_model = get_user_model()
        users = user_model._base_manager
        inventory["users"] = {
            "total": users.count(),
            "active": users.filter(is_active=True).count(),
            "staff": users.filter(is_staff=True).count(),
            "superusers": users.filter(is_superuser=True).count(),
            "account_fingerprint": fingerprint(
                sorted(
                    (
                        user.get_username(),
                        user.password,
                        user.is_active,
                        user.is_staff,
                        user.is_superuser,
                    )
                    for user in users.all()
                )
            ),
        }

        groups = Group.objects.prefetch_related("permissions__content_type")
        group_assignments = sorted(
            (
                group.name,
                sorted(permission.natural_key() for permission in group.permissions.all()),
            )
            for group in groups
        )
        user_assignments = sorted(
            (
                user.get_username(),
                sorted(user.groups.values_list("name", flat=True)),
                sorted(
                    permission.natural_key()
                    for permission in user.user_permissions.select_related("content_type")
                ),
            )
            for user in users.prefetch_related("groups", "user_permissions__content_type")
        )
        inventory["permissions"] = {
            "permissions": Permission.objects.count(),
            "groups": Group.objects.count(),
            "user_permission_assignments": user_model.user_permissions.through.objects.count(),
            "user_group_memberships": user_model.groups.through.objects.count(),
            "group_permission_assignments": Group.permissions.through.objects.count(),
            "assignment_fingerprint": fingerprint(
                {
                    "groups": group_assignments,
                    "users": user_assignments,
                }
            ),
        }

        output_path = Path(options["output"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(inventory, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {connection.vendor} inventory for "
                f"{len(inventory['models'])} models to {output_path}"
            )
        )
