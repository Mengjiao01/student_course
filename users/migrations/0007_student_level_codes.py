from django.db import migrations, models


OLD_TO_NEW = {
    "undergraduate": "bachelor",
    "master": "master",
    "doctoral": "doctor",
}
NEW_TO_OLD = {value: key for key, value in OLD_TO_NEW.items()}


def forwards(apps, schema_editor):
    Student = apps.get_model("users", "Student")
    for old_value, new_value in OLD_TO_NEW.items():
        Student.objects.filter(level=old_value).update(level=new_value)


def backwards(apps, schema_editor):
    Student = apps.get_model("users", "Student")
    for new_value, old_value in NEW_TO_OLD.items():
        Student.objects.filter(level=new_value).update(level=old_value)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_student_profile_fields"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="student",
            name="level",
            field=models.CharField(
                blank=True,
                choices=[("bachelor", "Bachelor"), ("master", "Master"), ("doctor", "Doctor")],
                default="",
                max_length=20,
            ),
        ),
    ]
