from random import randint

from django.db import migrations, models


def _generate_identifier(prefix, used_values):
    while True:
        candidate = f"{prefix}{randint(0, 99999999):08d}"
        if candidate not in used_values:
            used_values.add(candidate)
            return candidate


def forwards(apps, schema_editor):
    Profile = apps.get_model("users", "Profile")
    Student = apps.get_model("users", "Student")
    Teacher = apps.get_model("users", "Teacher")

    student_ids = set()
    for student in Student.objects.order_by("id"):
        student.student_id = _generate_identifier("S", student_ids)
        student.save(update_fields=["student_id"])

    teacher_ids = set()
    for teacher in Teacher.objects.order_by("id"):
        teacher.staff_id = _generate_identifier("T", teacher_ids)
        teacher.save(update_fields=["staff_id"])

    admin_ids = set()
    for profile in Profile.objects.filter(role="admin").order_by("id"):
        profile.admin_id = _generate_identifier("A", admin_ids)
        profile.save(update_fields=["admin_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0008_user_identifier_refresh"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="admin_id",
            field=models.CharField(blank=True, max_length=9, null=True, unique=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
