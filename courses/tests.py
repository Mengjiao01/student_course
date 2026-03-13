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

    def test_course_list_returns_all_courses(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(reverse("student_course_list"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "course_list_loaded")
        self.assertEqual(len(payload["data"]["courses"]), 2)
        self.assertEqual(payload["data"]["courses"][0]["course_name"], "Software Testing")
        self.assertTrue(payload["data"]["courses"][0]["is_enrolled"])
        self.assertEqual(payload["data"]["courses"][1]["course_name"], "Operating Systems")

    def test_course_detail_returns_enrollment_status_and_teacher(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(reverse("student_course_detail", args=[self.course.id]))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        course_data = payload["data"]["course"]
        self.assertEqual(payload["code"], "course_detail_loaded")
        self.assertEqual(course_data["course_name"], "Software Testing")
        self.assertEqual(course_data["credits"], 3)
        self.assertEqual(course_data["teacher_name"], "teacher1")
        self.assertEqual(course_data["enrolled_count"], 1)
        self.assertEqual(course_data["capacity"], 2)
        self.assertTrue(course_data["is_enrolled"])
        self.assertFalse(course_data["is_full"])
        self.assertFalse(course_data["can_enroll"])

    def test_course_detail_marks_full_course_as_unavailable(self):
        other_user = User.objects.create_user(username="student2", password="pass123456")
        Profile.objects.create(user=other_user, role="student")
        other_student = Student.objects.create(user=other_user, student_id="S002")
        Enrollment.objects.create(student=other_student, course=self.other_course)
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(
            reverse("student_course_detail", args=[self.other_course.id])
        )

        self.assertEqual(response.status_code, 200)
        course_data = response.json()["data"]["course"]
        self.assertFalse(course_data["is_enrolled"])
        self.assertTrue(course_data["is_full"])
        self.assertFalse(course_data["can_enroll"])

    def test_course_detail_returns_404_for_unknown_course(self):
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

    def test_enrolled_course_list_returns_selected_courses_by_student_id(self):
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(
            reverse("student_enrolled_course_list"),
            {"student_id": self.student.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "enrolled_courses_loaded")
        self.assertEqual(payload["data"]["student_id"], self.student.id)
        self.assertEqual(
            payload["data"]["courses"],
            [
                {
                    "course_id": self.course.id,
                    "course_name": "Software Testing",
                }
            ],
        )

    def test_enrolled_course_list_rejects_other_student_id(self):
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

    def test_enrolled_course_list_returns_404_for_unknown_student(self):
        self.client.login(username="student1", password="pass123456")

        response = self.client.get(
            reverse("student_enrolled_course_list"),
            {"student_id": 9999},
        )

        self.assertEqual(response.status_code, 404)
        self.assertJSONEqual(
            response.content,
            {
                "success": False,
                "code": "student_not_found",
                "message": "Student not found.",
                "data": {},
            },
        )
