from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_teacher_contact_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="student",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="student",
            name="program_duration",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="student",
            name="level",
            field=models.CharField(blank=True, choices=[("undergraduate", "??"), ("master", "??"), ("doctoral", "??")], default="", max_length=20),
        ),
    ]
