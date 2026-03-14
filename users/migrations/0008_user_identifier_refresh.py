from random import randint

from django.db import migrations, models


def _generate_identifier(prefix, used_values):
    while True:
        candidate = f"{prefix}{randint(0, 99999):05d}"
        if candidate not in used_values:
            used_values.add(candidate)
            return candidate


def forwards(apps, schema_editor):
    Profile = apps.get_model("users", "Profile")
    Student = apps.get_model("users", "Student")
    Teacher = apps.get_model("users", "Teacher")

    used_student_ids = set()
    used_teacher_ids = set()
    used_admin_ids = set()

    for student in Student.objects.order_by("id"):
        student.student_id = _generate_identifier("S", used_student_ids)
        student.save(update_fields=["student_id"])

    for teacher in Teacher.objects.order_by("id"):
        teacher.staff_id = _generate_identifier("T", used_teacher_ids)
        teacher.save(update_fields=["staff_id"])

    for profile in Profile.objects.filter(role="admin").order_by("id"):
        profile.admin_id = _generate_identifier("A", used_admin_ids)
        profile.save(update_fields=["admin_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_student_level_codes"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="admin_id",
            field=models.CharField(blank=True, max_length=6, null=True, unique=True),
        ),
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]
