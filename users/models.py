from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    # Store major directly on the student record so roster pages can read it
    # without introducing another profile table.
    major = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} - {self.student_id}"

    def display_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=100, blank=True, default="")
    department = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} - {self.staff_id}"

    def display_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username
