from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from enrollments.models import Enrollment
from users.models import Student
from users.utils import get_user_role

from .models import Course


def _json_response(success, message, *, data=None, status=200, code=None):
    return JsonResponse(
        {
            "success": success,
            "code": code,
            "message": message,
            "data": data or {},
        },
        status=status,
    )


def _require_student(request):
    if not request.user.is_authenticated:
        return None, _json_response(
            False,
            "Authentication is required.",
            status=401,
            code="authentication_required",
        )

    if get_user_role(request.user) != "student":
        return None, _json_response(
            False,
            "Only students can view course data.",
            status=403,
            code="invalid_role",
        )

    return get_object_or_404(Student, user=request.user), None


def _get_requested_student(request, current_student):
    student_id = request.GET.get("student_id")
    if not student_id:
        return current_student, None

    requested_student = Student.objects.filter(pk=student_id).first()
    if requested_student is None:
        return None, _json_response(
            False,
            "Student not found.",
            status=404,
            code="student_not_found",
        )

    # Students are only allowed to read their own enrollment list even if the
    # frontend submits a student id explicitly.
    if requested_student.id != current_student.id:
        return None, _json_response(
            False,
            "You can only view your own enrolled courses.",
            status=403,
            code="forbidden_student_access",
        )

    return requested_student, None


def _build_course_detail(course, *, is_enrolled):
    teacher_name = ""
    if course.teacher and course.teacher.user:
        teacher_name = course.teacher.user.username

    enrolled_count = course.enrolled_total
    is_full = enrolled_count >= course.capacity

    # The frontend can use these flags directly to decide whether the
    # existing enrollment API should enable or disable the enroll button.
    return {
        "id": course.id,
        "course_name": course.course_name,
        "credits": course.credits,
        "teacher_name": teacher_name,
        "enrolled_count": enrolled_count,
        "capacity": course.capacity,
        "is_enrolled": is_enrolled,
        "is_full": is_full,
        "can_enroll": not is_enrolled and not is_full,
    }


@require_GET
def student_course_list(request):
    student, error_response = _require_student(request)
    if error_response is not None:
        return error_response

    enrolled_course_ids = set(
        Enrollment.objects.filter(student=student).values_list("course_id", flat=True)
    )
    courses = (
        Course.objects.select_related("teacher__user")
        .annotate(enrolled_total=Count("enrollment"))
        .order_by("id")
    )

    # The list response stays lightweight because the page only needs enough
    # data to render the course menu and navigate to a detail request.
    course_items = [
        {
            "id": course.id,
            "course_name": course.course_name,
            "is_enrolled": course.id in enrolled_course_ids,
        }
        for course in courses
    ]

    return _json_response(
        True,
        "Course list loaded successfully.",
        data={"courses": course_items},
        code="course_list_loaded",
    )


@require_GET
def student_course_detail(request, course_id):
    student, error_response = _require_student(request)
    if error_response is not None:
        return error_response

    course = (
        Course.objects.select_related("teacher__user")
        .annotate(enrolled_total=Count("enrollment"))
        .filter(pk=course_id)
        .first()
    )
    if course is None:
        return _json_response(
            False,
            "Course not found.",
            status=404,
            code="course_not_found",
        )

    is_enrolled = Enrollment.objects.filter(student=student, course=course).exists()

    return _json_response(
        True,
        "Course detail loaded successfully.",
        data={"course": _build_course_detail(course, is_enrolled=is_enrolled)},
        code="course_detail_loaded",
    )


@require_GET
def student_enrolled_course_list(request):
    current_student, error_response = _require_student(request)
    if error_response is not None:
        return error_response

    student, error_response = _get_requested_student(request, current_student)
    if error_response is not None:
        return error_response

    enrollments = (
        Enrollment.objects.filter(student=student)
        .select_related("course")
        .order_by("course_id", "id")
    )

    # The frontend mainly needs the selected course names, but returning the
    # course id as well makes navigation to the course detail page straightforward.
    courses = [
        {
            "course_id": enrollment.course.id,
            "course_name": enrollment.course.course_name,
        }
        for enrollment in enrollments
    ]

    return _json_response(
        True,
        "Enrolled courses loaded successfully.",
        data={
            "student_id": student.id,
            "courses": courses,
        },
        code="enrolled_courses_loaded",
    )
