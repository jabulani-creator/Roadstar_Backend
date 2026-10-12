from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("fleet", "0005_instructorprofile_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="instructorprofile",
            name="photo_focus",
            field=models.CharField(
                choices=[
                    ("center", "Center — full face in frame"),
                    ("top", "Top — prefer upper body / standing shots"),
                    ("bottom", "Bottom — prefer lower framing"),
                ],
                default="center",
                help_text="How the public card crops the photo.",
                max_length=16,
            ),
        ),
    ]
