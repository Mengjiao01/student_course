import json

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from courses.models import Course
from users.models import Student

from .models import Enrollment


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


def _get_user_role(user):
    if user.is_superuser:
        return "admin"

    profile = getattr(user, "profile", None)
    if profile is None:
        return None

    return profile.role


def _get_course_id(request):
    if request.content_type == "application/json":
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None
        return payload.get("course_id")

    return request.POST.get("course_id")


@require_POST
def create_enrollment(request):
    if not request.user.is_authenticated:
        return _json_response(
            False,
            "Authentication is required.",
            status=401,
            code="authentication_required",
        )

    if _get_user_role(request.user) != "student":
        return _json_response(
            False,
            "Only students can enroll in courses.",
            status=403,
            code="invalid_role",
        )

    student = get_object_or_404(Student, user=request.user)
    course_id = _get_course_id(request)

    if not course_id:
        return _json_response(
            False,
            "The 'course_id' parameter is required.",
            status=400,
            code="missing_course_id",
        )

    #course check
    with transaction.atomic():
        course = Course.objects.select_for_update().filter(pk=course_id).first()
        if course is None:
            return _json_response(
                False,
                "Course not found.",
                status=404,
                code="course_not_found",
            )

        #avoid duplicate selections
        if Enrollment.objects.filter(student=student, course=course).exists():
            return _json_response(
                False,
                "You are already enrolled in this course.",
                status=409,
                code="duplicate_enrollment",
            )

        #check cappacity
        if course.enrolled_count() >= course.capacity:
            return _json_response(
                False,
                "This course is already full.",
                status=409,
                code="course_full",
            )

        try:
            enrollment = Enrollment.objects.create(student=student, course=course)
        except IntegrityError:
            return _json_response(
                False,
                "You are already enrolled in this course.",
                status=409,
                code="duplicate_enrollment",
            )

    return _json_response(
        True,
        "Enrollment created successfully.",
        data={
            "enrollment_id": enrollment.id,
            "student_id": student.id,
            "course_id": course.id,
            "course_name": course.course_name,
        },
        status=201,
        code="enrollment_created",
    )
