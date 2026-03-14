from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_remove_teacher_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacher",
            name="office_phone",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AddField(
            model_name="teacher",
            name="title",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
