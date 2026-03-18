from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from enrollments.models import Enrollment
from users.models import Profile, Student, Teacher

from .models import Course


class StudentCourseApiTests(TestCase):
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
        self.teacher = Teacher.objects.create(user=self.teacher_user, staff_id="T001")

        self.course = Course.objects.create(
            course_code="CS101",
            course_name="Software Testing",
            credits=3,
            capacity=2,
            teacher=self.teacher,
        )
        self.other_course = Course.objects.create(
            course_code="CS102",
            course_name="Operating Systems",
            credits=4,
            capacity=1,
        )

    def test_course_list_requires_student_login(self):
        # Ensure the student course API rejects unauthenticated access.
        response = self.client.get(reverse("student_course_list"))

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

    def test_course_detail_returns_404_for_unknown_course(self):
        # Verify the detail API reports a missing course with a 404 response.
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(reverse("student_course_detail", args=[9999]))

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "course_not_found",
                "message": "Course not found.",
                "data": {},
            },
        )

    def test_enrolled_course_list_rejects_other_student_id(self):
        # Confirm students cannot use the API to inspect another student's course list.
        other_user = User.objects.create_user(username="student2", password="pass123456")
        Profile.objects.create(user=other_user, role="student")
        other_student = Student.objects.create(user=other_user, student_id="S002")
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(
            reverse("student_enrolled_course_list"),
            {"student_id": other_student.id},
        )

        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "forbidden_student_access",
                "message": "You can only view your own enrolled courses.",
                "data": {},
            },
        )
