from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from courses.models import Course
from enrollments.models import Enrollment
from users.models import Profile, Student, Teacher


class LoginViewTests(TestCase):
    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student1",
            password="pass123456",
        )
        Profile.objects.create(user=self.student_user, role="student")
        Student.objects.create(
            user=self.student_user,
            student_id="S001",
            major="Computer Science",
        )

        self.teacher_user = User.objects.create_user(
            username="teacher1",
            password="teacher123456",
        )
        Profile.objects.create(user=self.teacher_user, role="teacher")
        Teacher.objects.create(
            user=self.teacher_user,
            staff_id="T001",
        )

        self.admin_user = User.objects.create_user(
            username="admin1",
            password="admin123456",
            email="admin@example.com",
        )
        Profile.objects.create(user=self.admin_user, role="admin", admin_id="A0000001")

    def test_student_login_success_redirects_to_student_dashboard(self):
        # Verify that a valid student ID and password log into the student area.
        response = self.client.post(
            reverse("login"),
            {
                "login_id": "S001",
                "password": "pass123456",
                "role": "student",
            },
        )

        self.assertRedirects(response, reverse("student_dashboard"))

    def test_login_rejects_wrong_password(self):
        # Ensure login fails with a clear error when the password is incorrect.
        response = self.client.post(
            reverse("login"),
            {
                "login_id": "S001",
                "password": "wrong-password",
                "role": "student",
            },
        )

        self.assertContains(response, "Invalid ID or password.")

    def test_login_rejects_role_mismatch(self):
        # Confirm the form detects accounts logged in under the wrong selected role.
        response = self.client.post(
            reverse("login"),
            {
                "login_id": "S001",
                "password": "pass123456",
                "role": "teacher",
            },
        )

        self.assertContains(response, "The selected role does not match this account.")

    def test_admin_id_login_redirects_to_admin_dashboard(self):
        # Check that admins can authenticate using the business admin ID field.
        response = self.client.post(
            reverse("login"),
            {
                "login_id": "A0000001",
                "password": "admin123456",
                "role": "admin",
            },
        )

        self.assertRedirects(response, reverse("admin_dashboard"))


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="stu1", password="pass123456")
        Profile.objects.create(user=self.user, role="student")
        self.student = Student.objects.create(
            user=self.user,
            student_id="S1001",
            major="Software Engineering",
        )
        self.course = Course.objects.create(
            course_name="Python Programming",
            credits=3,
            capacity=2,
        )

    def test_student_dashboard_stats_show_enrollment_count_and_total_credits(self):
        # Validate the dashboard summary cards reflect the student's current enrollments.
        Enrollment.objects.create(student=self.student, course=self.course)
        self.client.login(username="stu1", password="pass123456")

        response = self.client.get(reverse("student_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["enrolled_course_count"], 1)
        self.assertEqual(response.context["total_credits"], 3)
        self.assertContains(response, "Total Credits")

    def test_student_can_enroll_course(self):
        # Verify a student can enroll from the dashboard and create an enrollment record.
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
        # Verify a student can drop an enrolled course from the dashboard.
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
class TeacherDashboardTests(TestCase):
    def setUp(self):
        self.teacher_user = User.objects.create_user(
            username="teacher1",
            password="pass123456",
        )
        Profile.objects.create(user=self.teacher_user, role="teacher")
        self.teacher = Teacher.objects.create(user=self.teacher_user, staff_id="T001")

        self.other_teacher_user = User.objects.create_user(
            username="teacher2",
            password="pass123456",
        )
        Profile.objects.create(user=self.other_teacher_user, role="teacher")
        self.other_teacher = Teacher.objects.create(
            user=self.other_teacher_user,
            staff_id="T002",
        )

        self.course_alpha = Course.objects.create(
            course_code="CS101",
            course_name="Algorithms",
            schedule="Monday 09:00-11:00",
            location="Room A101",
            start_date=date(2026, 2, 16),
            end_date=date(2026, 6, 20),
            delivery_mode="lecture",
            credits=3,
            capacity=30,
            teacher=self.teacher,
        )
        self.course_beta = Course.objects.create(
            course_code="CS205",
            course_name="Data Structures",
            schedule="Wednesday 14:00-16:00",
            location="Room B202",
            start_date=date(2026, 2, 16),
            end_date=date(2026, 6, 20),
            delivery_mode="seminar",
            credits=4,
            capacity=25,
            teacher=self.teacher,
        )
        Course.objects.create(
            course_code="MATH300",
            course_name="Linear Algebra",
            credits=3,
            capacity=20,
            teacher=self.other_teacher,
        )

    def test_teacher_course_students_shows_course_details_and_students(self):
        # Confirm teachers can view the roster and course summary for their own course.
        student_user = User.objects.create_user(username="alice", password="pass123456")
        Profile.objects.create(user=student_user, role="student")
        student = Student.objects.create(
            user=student_user,
            student_id="S1002",
            major="Artificial Intelligence",
        )
        Enrollment.objects.create(student=student, course=self.course_alpha)

        self.client.login(username="teacher1", password="pass123456")
        response = self.client.get(
            reverse("teacher_course_students", args=[self.course_alpha.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Roster")
        self.assertContains(response, "CS101")
        self.assertContains(response, "Monday 09:00-11:00")
        self.assertContains(response, "alice")
        self.assertContains(response, "S1002")
        self.assertContains(response, "Artificial Intelligence")

    def test_teacher_course_students_rejects_other_teachers_course(self):
        # Ensure a teacher cannot open the roster page for a course they do not teach.
        self.client.login(username="teacher2", password="pass123456")

        response = self.client.get(
            reverse("teacher_course_students", args=[self.course_alpha.id])
        )

        self.assertEqual(response.status_code, 404)


class AdminDetailModalTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin_modal",
            password="admin123456",
            email="admin_modal@example.com",
        )
        teacher_user = User.objects.create_user(
            username="teacher_modal",
            password="pass123456",
            first_name="Mia",
            last_name="Chen",
            email="mia.chen@example.com",
        )
        student_user = User.objects.create_user(
            username="student_modal",
            password="pass123456",
            first_name="Evan",
            last_name="Liu",
            email="evan.liu@example.com",
        )
        Profile.objects.create(user=teacher_user, role="teacher")
        Profile.objects.create(user=student_user, role="student")
        self.teacher = Teacher.objects.create(
            user=teacher_user,
            staff_id="T900",
            department="Engineering",
            office_phone="020-7946-0123",
            title="Associate Professor",
        )
        self.student = Student.objects.create(
            user=student_user,
            student_id="S900",
            major="Data Science",
            phone="13800138000",
            program_duration="4 years",
            level="bachelor",
        )

    def test_admin_teacher_detail_modal_returns_json(self):
        # Check the teacher detail endpoint returns the modal payload expected by the UI.
        self.client.login(username="admin_modal", password="admin123456")

        response = self.client.get(reverse("admin_teacher_detail_modal", args=[self.teacher.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Teacher Details")
        self.assertEqual(response.json()["fields"][0]["value"], "T900")
        self.assertEqual(response.json()["fields"][3]["value"], "020-7946-0123")
        self.assertEqual(response.json()["fields"][4]["value"], "mia.chen@example.com")
        self.assertEqual(response.json()["fields"][5]["value"], "Associate Professor")
        self.assertEqual(len(response.json()["fields"]), 6)

    def test_admin_student_detail_modal_returns_json(self):
        # Check the student detail endpoint returns the modal payload expected by the UI.
        self.client.login(username="admin_modal", password="admin123456")

        response = self.client.get(reverse("admin_student_detail_modal", args=[self.student.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["title"], "Student Details")
        self.assertEqual(response.json()["fields"][0]["value"], "S900")
        self.assertEqual(response.json()["fields"][3]["value"], "13800138000")
        self.assertEqual(response.json()["fields"][4]["value"], "evan.liu@example.com")
        self.assertEqual(response.json()["fields"][5]["value"], "4 years")
        self.assertEqual(response.json()["fields"][6]["value"], "Bachelor")
        self.assertEqual(len(response.json()["fields"]), 7)




