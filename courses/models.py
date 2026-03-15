from django.db import models
from users.models import Teacher


class Course(models.Model):
    # Delivery mode is stored as choices so templates can use
    # get_delivery_mode_display() without custom mapping code.
    DELIVERY_MODE_CHOICES = [
        ("lecture", "Lecture"),
        ("seminar", "Seminar"),
        ("lab", "Lab"),
        ("tutorial", "Tutorial"),
    ]

    course_code = models.CharField(max_length=20, blank=True, default="")
    course_name = models.CharField(max_length=100)
    schedule = models.CharField(max_length=100, blank=True, default="")
    location = models.CharField(max_length=100, blank=True, default="")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    delivery_mode = models.CharField(
        max_length=20,
        choices=DELIVERY_MODE_CHOICES,
        default="lecture",
    )
    credits = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField(default=50)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)
    teachers = models.ManyToManyField(
        Teacher,
        blank=True,
        related_name="courses",
    )

    def __str__(self):
        return self.course_code or self.course_name

    def enrolled_count(self):
        # Centralize the enrollment count so templates and views share one source.
        return self.enrollment_set.count()

    def meeting_display(self):
        # Teacher pages present schedule and location as one compact label.
        parts = [part for part in [self.schedule, self.location] if part]
        return " | ".join(parts)

    def teacher_list(self):
        # Prefer the many-to-many assignments, but keep the legacy single-teacher fallback.
        assigned_teachers = list(self.teachers.select_related("user").all())
        if assigned_teachers:
            return assigned_teachers
        if self.teacher_id:
            return [self.teacher]
        return []

    def teacher_names_display(self):
        # Collapse the teacher objects into a template-friendly display string.
        names = [teacher.display_name() for teacher in self.teacher_list()]
        return ", ".join(filter(None, names))
