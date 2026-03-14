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
    admin_id = models.CharField(max_length=9, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Student(models.Model):
    LEVEL_CHOICES = [
        ("bachelor", "Bachelor"),
        ("master", "Master"),
        ("doctor", "Doctor"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    student_id = models.CharField(max_length=20, unique=True)
    # Store major directly on the student record so roster pages can read it
    # without introducing another profile table.
    major = models.CharField(max_length=100, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    program_duration = models.CharField(max_length=30, blank=True, default="")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} - {self.student_id}"

    def display_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=100, blank=True, default="")
    office_phone = models.CharField(max_length=30, blank=True, default="")
    title = models.CharField(max_length=100, blank=True, default="")

    def __str__(self):
        return f"{self.user.username} - {self.staff_id}"

    def display_name(self):
        full_name = self.user.get_full_name().strip()
        return full_name or self.user.username
