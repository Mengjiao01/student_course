from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from enrollments.models import Enrollment
from users.models import Profile, Student


class LoginViewTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student1",
            password="pass123456",
        )
        Profile.objects.create(user=self.student_user, role="student")
        Student.objects.create(user=self.student_user, student_id="S001")

        self.admin_user = User.objects.create_superuser(
            username="admin1",
            password="admin123456",
            email="admin@example.com",
        )

    def test_student_login_success_redirects_to_student_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "student1",
                "password": "pass123456",
                "role": "student",
            },
        )

        self.assertRedirects(response, reverse("student_dashboard"))

    def test_login_rejects_wrong_password(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "student1",
                "password": "wrong-password",
                "role": "student",
            },
        )

        self.assertContains(response, "Invalid username or password.")

    def test_login_rejects_role_mismatch(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "student1",
                "password": "pass123456",
                "role": "teacher",
            },
        )

        self.assertContains(response, "The selected role does not match this account.")

    def test_superuser_can_login_as_admin(self):
        response = self.client.post(
            reverse("login"),
            {
                "username": "admin1",
                "password": "admin123456",
                "role": "admin",
            },
        )

        self.assertRedirects(response, reverse("admin_dashboard"))


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stu1", password="pass123456")
        Profile.objects.create(user=self.user, role="student")
        self.student = Student.objects.create(user=self.user, student_id="S1001")
        self.course = Course.objects.create(
            course_name="Python Programming",
            credits=3,
            capacity=2,
        )

    def test_student_dashboard_shows_courses(self):
        self.client.login(username="stu1", password="pass123456")

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "View Courses")
        self.assertContains(response, "Python Programming")

    def test_student_can_enroll_course(self):
        self.client.login(username="stu1", password="pass123456")

        response = self.client.post(
            reverse("student_dashboard"),
            {"action": "enroll", "course_id": self.course.id, "tab": "courses"},
        )

        self.assertRedirects(response, f"{reverse('student_dashboard')}?tab=courses")
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )

    def test_student_can_withdraw_course(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="stu1", password="pass123456")

        response = self.client.post(
            reverse("student_dashboard"),
            {"action": "withdraw", "course_id": self.course.id, "tab": "enrolled"},
        )

        self.assertRedirects(response, f"{reverse('student_dashboard')}?tab=enrolled")
        self.assertFalse(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )
