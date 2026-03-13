from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0002_student_major"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacher",
            name="department",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="teacher",
            name="title",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
