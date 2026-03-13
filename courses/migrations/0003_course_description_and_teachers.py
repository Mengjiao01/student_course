import django.db.models.deletion
from django.db import migrations, models


def populate_course_teachers(apps, schema_editor):
    Course = apps.get_model("courses", "Course")
    for course in Course.objects.exclude(teacher_id__isnull=True):
        course.teachers.add(course.teacher_id)


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_teacher_profile_fields"),
        ("courses", "0002_course_teaching_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="course",
            name="capacity",
            field=models.PositiveIntegerField(default=50),
        ),
        migrations.AddField(
            model_name="course",
            name="teachers",
            field=models.ManyToManyField(blank=True, related_name="courses", to="users.teacher"),
        ),
        migrations.RunPython(populate_course_teachers, migrations.RunPython.noop),
    ]
