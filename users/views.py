from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from courses.models import Course
from enrollments.models import Enrollment

from .forms import AdminCourseForm, LoginForm
from .models import Profile, Student, Teacher
from .utils import get_user_role

# Keep the dashboard routing in one place so login and redirects stay consistent.
def _get_dashboard_url(role):
    role_to_url = {
        "student": "student_dashboard",
        "teacher": "teacher_dashboard",
        "admin": "admin_dashboard",
    }
    return role_to_url[role]


def _admin_only(request):
    # Reuse the same guard across all admin-facing views.
    if get_user_role(request.user) != "admin":
        return HttpResponseForbidden("You do not have permission to access this page.")
    return None


def _teacher_detail_payload(teacher):
    # The admin detail modal expects a flat title/fields payload.
    return {
        "title": "Teacher Details",
        "fields": [
            {"label": "Teacher ID", "value": teacher.staff_id},
            {"label": "Teacher Name", "value": teacher.display_name()},
            {"label": "Department", "value": teacher.department or "Not set"},
            {"label": "Office Phone", "value": teacher.office_phone or "Not set"},
            {"label": "Email", "value": teacher.user.email or "Not set"},
            {"label": "Title", "value": teacher.title or "Not set"},
        ],
    }


def _student_detail_payload(student):
    # The student modal uses the same payload shape as the teacher modal.
    return {
        "title": "Student Details",
        "fields": [
            {"label": "Student ID", "value": student.student_id},
            {"label": "Student Name", "value": student.display_name()},
            {"label": "Major", "value": student.major or "Not set"},
            {"label": "Phone", "value": student.phone or "Not set"},
            {"label": "Email", "value": student.user.email or "Not set"},
            {"label": "Year", "value": student.program_duration or "Not set"},
            {"label": "Study Level", "value": student.get_level_display() or "Not set"},
        ],
    }


def _teacher_course_queryset():
    # Load related teacher records up front to avoid repeated queries in templates.
    return Course.objects.select_related("teacher__user").prefetch_related("teachers__user")


def _course_admin_queryset():
    # Admin and student pages both need teacher data plus an enrollment total.
    return (
        Course.objects.select_related("teacher__user")
        .prefetch_related("teachers__user")
        .annotate(enrolled_total=Count("enrollment", distinct=True))
    )


def _get_login_user(selected_role, login_id):
    # Resolve the submitted business ID against the selected role only.
    if selected_role == "student":
        student = Student.objects.select_related("user").filter(student_id=login_id).first()
        return student.user if student else None

    if selected_role == "teacher":
        teacher = Teacher.objects.select_related("user").filter(staff_id=login_id).first()
        return teacher.user if teacher else None

    profile = Profile.objects.select_related("user").filter(role="admin", admin_id=login_id).first()
    return profile.user if profile else None


def _get_login_user_by_any_id(login_id):
    # Use a broader lookup to detect "valid ID but wrong role" cases.
    student = Student.objects.select_related("user").filter(student_id=login_id).first()
    if student:
        return student.user

    teacher = Teacher.objects.select_related("user").filter(staff_id=login_id).first()
    if teacher:
        return teacher.user

    profile = Profile.objects.select_related("user").filter(admin_id=login_id).first()
    return profile.user if profile else None


@ensure_csrf_cookie
def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        # Pull the cleaned credentials once so the flow below stays readable.
        login_id = form.cleaned_data["login_id"].strip()
        password = form.cleaned_data["password"]
        selected_role = form.cleaned_data["role"]

        user = _get_login_user(selected_role, login_id)
        if user is not None:
            # Password validation happens after the business ID resolves to a user.
            if not user.check_password(password):
                form.add_error(None, "Invalid ID or password.")
            else:
                login(request, user)
                return redirect(_get_dashboard_url(selected_role))
        else:
            # A second lookup lets the UI explain role mismatches more clearly.
            user = _get_login_user_by_any_id(login_id)
            if user is not None and user.check_password(password):
                form.add_error(None, "The selected role does not match this account.")
            else:
                form.add_error(None, "Invalid ID or password.")

    return render(request, "users/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_redirect(request):
    role = get_user_role(request.user)
    if role is None:
        return redirect("login")

    return redirect(_get_dashboard_url(role))


def _handle_student_enrollment(request, student):
    # Route both enroll and withdraw actions through one POST handler.
    action = request.POST.get("action")
    course_id = request.POST.get("course_id")

    if action not in {"enroll", "withdraw"} or not course_id:
        messages.error(request, "The submitted action is invalid.")
        return

    course = get_object_or_404(Course, pk=course_id)

    if action == "enroll":
        # Prevent duplicate rows before checking seat availability.
        if Enrollment.objects.filter(student=student, course=course).exists():
            messages.warning(request, "You are already enrolled in this course.")
            return

        if course.enrolled_count() >= course.capacity:
            messages.error(request, "This course is full and cannot accept more enrollments.")
            return

        Enrollment.objects.create(student=student, course=course)
        messages.success(request, "Enrollment successful.")
        return

    # Withdraw by removing the student's enrollment row for that course.
    deleted_count, _ = Enrollment.objects.filter(student=student, course=course).delete()
    if deleted_count:
        messages.success(request, "Course dropped successfully.")
    else:
        messages.warning(request, "You are not enrolled in this course.")


@never_cache
@login_required
def student_dashboard(request):
    if get_user_role(request.user) != "student":
        return HttpResponseForbidden("You do not have permission to access this page.")

    student = get_object_or_404(Student, user=request.user)

    if request.method == "POST":
        # Send the user back to the tab they submitted from after the action completes.
        _handle_student_enrollment(request, student)
        active_tab = request.POST.get("tab", "courses")
        return redirect(f"{request.path}?tab={active_tab}")

    active_tab = request.GET.get("tab", "")
    if active_tab not in {"", "courses", "enrolled"}:
        active_tab = ""

    all_courses = _course_admin_queryset().order_by("id")
    enrolled_course_ids = set(
        Enrollment.objects.filter(student=student).values_list("course_id", flat=True)
    )
    enrolled_courses = all_courses.filter(id__in=enrolled_course_ids)
    total_credits = sum(course.credits for course in enrolled_courses)

    # Keep the two dashboard tables paginated independently.
    all_courses_page_obj = Paginator(all_courses, 10).get_page(request.GET.get("courses_page"))
    enrolled_courses_page_obj = Paginator(enrolled_courses, 10).get_page(
        request.GET.get("enrolled_page")
    )

    context = {
        "student": student,
        "active_tab": active_tab,
        "all_courses": all_courses_page_obj.object_list,
        "all_courses_page_obj": all_courses_page_obj,
        "enrolled_courses": enrolled_courses_page_obj.object_list,
        "enrolled_courses_page_obj": enrolled_courses_page_obj,
        "enrolled_course_ids": enrolled_course_ids,
        "enrolled_course_count": len(enrolled_course_ids),
        "total_credits": total_credits,
    }
    return render(request, "users/student_dashboard.html", context)


@login_required
def teacher_dashboard(request):
    if get_user_role(request.user) != "teacher":
        return HttpResponseForbidden("You do not have permission to access this page.")

    teacher = get_object_or_404(Teacher, user=request.user)
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name")

    # Teachers can see courses from either the legacy single-teacher field
    # or the newer many-to-many assignment list.
    course_list = (
        _teacher_course_queryset()
        .filter(Q(teacher=teacher) | Q(teachers=teacher))
        .annotate(enrolled_total=Count("enrollment", distinct=True))
        .distinct()
    )
    if query:
        course_list = course_list.filter(
            Q(course_name__icontains=query) | Q(course_code__icontains=query)
        )

    # Map the UI sort options to concrete ORM order clauses.
    sort_map = {
        "name": "course_name",
        "name_desc": "-course_name",
        "schedule": "schedule",
        "schedule_desc": "-schedule",
        "code": "course_code",
        "code_desc": "-course_code",
    }
    course_list = course_list.order_by(sort_map.get(sort, "course_name"), "id")
    paginator = Paginator(course_list, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "users/teacher_dashboard.html",
        {
            "teacher": teacher,
            "courses": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "sort": sort,
        },
    )


@login_required
def teacher_course_students(request, course_id):
    if get_user_role(request.user) != "teacher":
        return HttpResponseForbidden("You do not have permission to access this page.")

    teacher = get_object_or_404(Teacher, user=request.user)
    course = get_object_or_404(_teacher_course_queryset().distinct(), pk=course_id)
    if teacher not in course.teacher_list():
        raise Http404("Course not found.")

    query = request.GET.get("q", "").strip()

    # Load roster entries with their student account in one query.
    enrollments = Enrollment.objects.filter(course=course).select_related(
        "student__user"
    ).order_by("student__student_id", "id")
    if query:
        enrollments = enrollments.filter(
            Q(student__student_id__icontains=query)
            | Q(student__user__username__icontains=query)
            | Q(student__user__first_name__icontains=query)
            | Q(student__user__last_name__icontains=query)
        )

    paginator = Paginator(enrollments, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "users/teacher_course_students.html",
        {
            "course": course,
            "page_obj": page_obj,
            "query": query,
        },
    )


@login_required
def admin_dashboard(request):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    return render(request, "users/admin_dashboard.html", {"admin_id": request.user.profile.admin_id})


@login_required
def admin_course_list(request):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    query = request.GET.get("q", "").strip()
    delivery_mode = request.GET.get("delivery_mode", "").strip()

    courses = _course_admin_queryset().order_by("course_code", "id")
    if query:
        courses = courses.filter(
            Q(course_code__icontains=query)
            | Q(course_name__icontains=query)
            | Q(location__icontains=query)
            | Q(teacher__user__username__icontains=query)
            | Q(teacher__user__first_name__icontains=query)
            | Q(teacher__user__last_name__icontains=query)
            | Q(teachers__user__username__icontains=query)
            | Q(teachers__user__first_name__icontains=query)
            | Q(teachers__user__last_name__icontains=query)
        )
    if delivery_mode:
        courses = courses.filter(delivery_mode=delivery_mode)

    courses = courses.distinct()
    paginator = Paginator(courses, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "users/admin_course_list.html",
        {
            "page_obj": page_obj,
            "query": query,
            "delivery_mode": delivery_mode,
            "delivery_mode_choices": Course.DELIVERY_MODE_CHOICES,
        },
    )


@login_required
def admin_course_create(request):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    form = AdminCourseForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        messages.success(request, f"Course {course.course_name} has been published.")
        return redirect("admin_course_list")

    return render(
        request,
        "users/admin_course_form.html",
        {
            "form": form,
            "page_title": "Publish Course",
            "submit_label": "Publish Course",
            "is_edit": False,
        },
    )


@login_required
def admin_course_edit(request, course_id):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    course = get_object_or_404(_course_admin_queryset(), pk=course_id)
    form = AdminCourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        course = form.save()
        messages.success(request, f"Course {course.course_name} has been updated.")
        return redirect("admin_course_detail", course_id=course.id)

    return render(
        request,
        "users/admin_course_form.html",
        {
            "form": form,
            "course": course,
            "page_title": "Edit Course",
            "submit_label": "Save Changes",
            "is_edit": True,
        },
    )


@login_required
def admin_course_detail(request, course_id):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    course = get_object_or_404(_course_admin_queryset(), pk=course_id)

    teacher_query = request.GET.get("teacher_q", "").strip()
    student_query = request.GET.get("student_q", "").strip()

    # Teacher assignments are already materialized as objects, so filter them in Python.
    teachers = course.teacher_list()
    if teacher_query:
        lowered_query = teacher_query.lower()
        teachers = [
            teacher for teacher in teachers
            if lowered_query in teacher.staff_id.lower()
            or lowered_query in teacher.department.lower()
        ]
    teacher_page_obj = Paginator(teachers, 5).get_page(request.GET.get("teacher_page"))

    # Student roster filtering stays in SQL because the list can grow much larger.
    enrollments = Enrollment.objects.filter(course=course).select_related("student__user")
    if student_query:
        enrollments = enrollments.filter(
            Q(student__student_id__icontains=student_query)
            | Q(student__major__icontains=student_query)
        )
    student_page_obj = Paginator(
        enrollments.order_by("student__student_id", "id"),
        10,
    ).get_page(request.GET.get("student_page"))

    return render(
        request,
        "users/admin_course_detail.html",
        {
            "course": course,
            "teacher_page_obj": teacher_page_obj,
            "student_page_obj": student_page_obj,
            "teacher_query": teacher_query,
            "student_query": student_query,
        },
    )


@login_required
def admin_teacher_detail_modal(request, teacher_id):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    teacher = get_object_or_404(Teacher.objects.select_related("user"), pk=teacher_id)
    # Return JSON because the modal is rendered client-side.
    return JsonResponse(_teacher_detail_payload(teacher))


@login_required
def admin_student_detail_modal(request, student_id):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    student = get_object_or_404(Student.objects.select_related("user"), pk=student_id)
    # Return JSON because the modal is rendered client-side.
    return JsonResponse(_student_detail_payload(student))



