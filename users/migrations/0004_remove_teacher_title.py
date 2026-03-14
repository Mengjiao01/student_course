from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_teacher_profile_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="teacher",
            name="title",
        ),
    ]
