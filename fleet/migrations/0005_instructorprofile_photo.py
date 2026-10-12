from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0004_vehicle_photo_imagefield"),
    ]

    operations = [
        migrations.AddField(
            model_name="instructorprofile",
            name="photo",
            field=models.ImageField(
                blank=True,
                help_text="Public profile photo. Leave blank to show the placeholder.",
                upload_to="fleet/instructors/",
            ),
        ),
    ]
