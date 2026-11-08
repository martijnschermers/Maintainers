from django.db import migrations


def create_default_site(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.update_or_create(
        id=1,
        defaults={"domain": "localhost:8000", "name": "Maintainers lokaal"},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("maintenance", "0001_initial"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [migrations.RunPython(create_default_site, migrations.RunPython.noop)]
