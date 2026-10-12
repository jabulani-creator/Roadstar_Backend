from django.db import migrations, models


def clear_legacy_photo_urls(apps, schema_editor):
    """Old CharField stored paths/URLs — clear before switching to ImageField."""
    Vehicle = apps.get_model("fleet", "Vehicle")
    Vehicle.objects.exclude(photo="").update(photo="")


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0003_vehicle_photo"),
    ]

    operations = [
        migrations.RunPython(clear_legacy_photo_urls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vehicle",
            name="photo",
            field=models.ImageField(
                blank=True,
                help_text=(
                    "Public cutout photo (transparent PNG preferred). "
                    "Leave blank to show the icon placeholder."
                ),
                upload_to="fleet/vehicles/",
            ),
        ),
    ]
