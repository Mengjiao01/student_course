from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course
from enrollments.models import Enrollment

from .forms import LoginForm
from .models import Student, Teacher
from .utils import get_user_role


def _get_dashboard_url(role):
    role_to_url = {
        "student": "student_dashboard",
        "teacher": "teacher_dashboard",
        "admin": "admin_dashboard",
    }
    return role_to_url[role]


def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        selected_role = form.cleaned_data["role"]

        # Authentication and role matching are checked separately so the UI
        # can report wrong credentials differently from a wrong role choice.
        user = authenticate(request, username=username, password=password)
        if user is None:
            form.add_error(None, "Invalid username or password.")
        else:
            actual_role = get_user_role(user)
            if actual_role != selected_role:
                form.add_error(None, "The selected role does not match this account.")
            else:
                login(request, user)
                return redirect(_get_dashboard_url(actual_role))

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
    action = request.POST.get("action")
    course_id = request.POST.get("course_id")

    if action not in {"enroll", "withdraw"} or not course_id:
        messages.error(request, "The submitted action is invalid.")
        return

    course = get_object_or_404(Course, pk=course_id)

    if action == "enroll":
        # Reject duplicates before checking capacity so the feedback stays precise.
        if Enrollment.objects.filter(student=student, course=course).exists():
            messages.warning(request, "You are already enrolled in this course.")
            return

        # The HTML flow enforces capacity here; the API path does the same inside
        # an atomic transaction to stay safe under concurrent requests.
        if course.enrolled_count() >= course.capacity:
            messages.error(request, "This course is full and cannot accept more enrollments.")
            return

        Enrollment.objects.create(student=student, course=course)
        messages.success(request, "Enrollment successful.")
        return

    deleted_count, _ = Enrollment.objects.filter(student=student, course=course).delete()
    if deleted_count:
        messages.success(request, "Course dropped successfully.")
    else:
        messages.warning(request, "You are not enrolled in this course.")


@login_required
def student_dashboard(request):
    if get_user_role(request.user) != "student":
        return HttpResponseForbidden("You do not have permission to access this page.")

    student = get_object_or_404(Student, user=request.user)

    if request.method == "POST":
        _handle_student_enrollment(request, student)
        active_tab = request.POST.get("tab", "courses")
        return redirect(f"{request.path}?tab={active_tab}")

    active_tab = request.GET.get("tab", "courses")
    if active_tab not in {"courses", "enrolled"}:
        active_tab = "courses"

    # Load teacher data and enrollment totals up front to avoid N+1 queries in the template.
    all_courses = (
        Course.objects.select_related("teacher__user")
        .annotate(enrolled_total=Count("enrollment"))
        .order_by("id")
    )
    enrolled_course_ids = set(
        Enrollment.objects.filter(student=student).values_list("course_id", flat=True)
    )
    enrolled_courses = all_courses.filter(id__in=enrolled_course_ids)

    context = {
        "student": student,
        "active_tab": active_tab,
        "all_courses": all_courses,
        "enrolled_courses": enrolled_courses,
        "enrolled_course_ids": enrolled_course_ids,
    }
    return render(request, "users/student_dashboard.html", context)


@login_required
def teacher_dashboard(request):
    if get_user_role(request.user) != "teacher":
        return HttpResponseForbidden("You do not have permission to access this page.")

    teacher = get_object_or_404(Teacher, user=request.user)
    query = request.GET.get("q", "").strip()
    sort = request.GET.get("sort", "name")

    course_list = Course.objects.filter(teacher=teacher).annotate(
        enrolled_total=Count("enrollment")
    )
    if query:
        # Teachers can find courses by either the public course code or the title.
        course_list = course_list.filter(
            Q(course_name__icontains=query) | Q(course_code__icontains=query)
        )

    sort_map = {
        "name": "course_name",
        "name_desc": "-course_name",
        "schedule": "schedule",
        "schedule_desc": "-schedule",
        "code": "course_code",
        "code_desc": "-course_code",
    }
    # Fall back to name ordering if an unknown sort key is submitted.
    course_list = course_list.order_by(sort_map.get(sort, "course_name"), "id")

    return render(
        request,
        "users/teacher_dashboard.html",
        {
            "teacher": teacher,
            "courses": course_list,
            "query": query,
            "sort": sort,
        },
    )


@login_required
def teacher_course_students(request, course_id):
    if get_user_role(request.user) != "teacher":
        return HttpResponseForbidden("You do not have permission to access this page.")

    teacher = get_object_or_404(Teacher, user=request.user)
    # Scope the course lookup by both id and teacher so one teacher cannot
    # inspect another teacher's roster by guessing course ids.
    course = get_object_or_404(Course, pk=course_id, teacher=teacher)
    query = request.GET.get("q", "").strip()

    enrollments = Enrollment.objects.filter(course=course).select_related(
        "student__user"
    ).order_by("student__student_id", "id")
    if query:
        # Search supports either the institutional student id or the login name.
        enrollments = enrollments.filter(
            Q(student__student_id__icontains=query)
            | Q(student__user__username__icontains=query)
        )

    # Pagination keeps large rosters responsive without changing the search contract.
    paginator = Paginator(enrollments, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "users/teacher_course_students.html",
        {
            "teacher": teacher,
            "course": course,
            "page_obj": page_obj,
            "query": query,
        },
    )


@login_required
def admin_dashboard(request):
    if get_user_role(request.user) != "admin":
        return HttpResponseForbidden("You do not have permission to access this page.")

    return render(request, "users/admin_dashboard.html", {"user": request.user})
