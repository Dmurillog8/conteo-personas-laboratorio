from django.db import migrations


def create_default_laboratory(apps, schema_editor):
    Laboratory = apps.get_model("core", "Laboratory")
    Laboratory.objects.get_or_create(
        name="Laboratorio P",
        defaults={
            "location": "Bloque P · Campus Universitario",
            "capacity": 200,
            "is_active": True,
        },
    )


def remove_default_laboratory(apps, schema_editor):
    Laboratory = apps.get_model("core", "Laboratory")
    Laboratory.objects.filter(
        name="Laboratorio P", location="Bloque P · Campus Universitario"
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_laboratory, remove_default_laboratory),
    ]
