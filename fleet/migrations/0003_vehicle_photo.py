from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("fleet", "0002_phase1_catalogue_fleet_public"),
    ]

    operations = [
        migrations.AddField(
            model_name="vehicle",
            name="photo",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Public cutout photo path or URL (transparent PNG preferred). "
                    "Leave blank to show the icon placeholder."
                ),
                max_length=500,
            ),
        ),
    ]
