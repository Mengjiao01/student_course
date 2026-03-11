from django.db import models
from users.models import Teacher


class Course(models.Model):
    course_name = models.CharField(max_length=100)
    credits = models.PositiveIntegerField()
    capacity = models.PositiveIntegerField()
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.course_name

    def enrolled_count(self):
        return self.enrollment_set.count()