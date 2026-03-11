import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from enrollments.models import Enrollment
from users.models import Profile, Student


class CreateEnrollmentApiTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student1",
            password="pass123456",
        )
        Profile.objects.create(user=self.student_user, role="student")
        self.student = Student.objects.create(user=self.student_user, student_id="S001")

        self.teacher_user = User.objects.create_user(
            username="teacher1",
            password="pass123456",
        )
        Profile.objects.create(user=self.teacher_user, role="teacher")

        self.course = Course.objects.create(
            course_name="Database Systems",
            credits=3,
            capacity=1,
        )

    def test_requires_authentication(self):
        response = self.client.post(reverse("create_enrollment"), {"course_id": self.course.id})

        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "authentication_required",
                "message": "Authentication is required.",
                "data": {},
            },
        )

    def test_rejects_non_student_role(self):
        self.client.login(username="teacher1", password="pass123456")

        response = self.client.post(reverse("create_enrollment"), {"course_id": self.course.id})

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "invalid_role",
                "message": "Only students can enroll in courses.",
                "data": {},
            },
        )

    def test_creates_enrollment_successfully(self):
        self.client.login(username="student1", password="pass123456")

        response = self.client.post(
            reverse("create_enrollment"),
            data=json.dumps({"course_id": self.course.id}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertEqual(payload["code"], "enrollment_created")
        self.assertEqual(payload["data"]["course_id"], self.course.id)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )

    def test_rejects_duplicate_enrollment(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="student1", password="pass123456")

        response = self.client.post(reverse("create_enrollment"), {"course_id": self.course.id})

        self.assertEqual(response.status_code, 409)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "duplicate_enrollment",
                "message": "You are already enrolled in this course.",
                "data": {},
            },
        )

    def test_rejects_full_course(self):
        other_user = User.objects.create_user(username="student2", password="pass123456")
        Profile.objects.create(user=other_user, role="student")
        other_student = Student.objects.create(user=other_user, student_id="S002")
        Enrollment.objects.create(student=other_student, course=self.course)

        self.client.login(username="student1", password="pass123456")
        response = self.client.post(reverse("create_enrollment"), {"course_id": self.course.id})

        self.assertEqual(response.status_code, 409)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "course_full",
                "message": "This course is already full.",
                "data": {},
            },
        )
