from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="course_code",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="course",
            name="delivery_mode",
            field=models.CharField(
                choices=[
                    ("lecture", "Lecture"),
                    ("seminar", "Seminar"),
                    ("lab", "Lab"),
                    ("tutorial", "Tutorial"),
                ],
                default="lecture",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="course",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="course",
            name="location",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="course",
            name="schedule",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="course",
            name="start_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
