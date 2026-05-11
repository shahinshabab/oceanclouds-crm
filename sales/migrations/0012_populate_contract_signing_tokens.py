import uuid

from django.db import migrations


def populate_contract_signing_tokens(apps, schema_editor):
    Contract = apps.get_model("sales", "Contract")

    for contract in Contract.objects.filter(signing_token__isnull=True):
        contract.signing_token = uuid.uuid4()
        contract.save(update_fields=["signing_token"])


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0011_contract_signed_at_contract_signed_by_name_and_more"),
    ]

    operations = [
        migrations.RunPython(
            populate_contract_signing_tokens,
            migrations.RunPython.noop,
        ),
    ]