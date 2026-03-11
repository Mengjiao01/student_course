from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from courses.models import Course
from enrollments.models import Enrollment

from .forms import LoginForm
from .models import Student


def _get_user_role(user):
    if user.is_superuser:
        return "admin"

    profile = getattr(user, "profile", None)
    if profile is None:
        return None

    return profile.role


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

        user = authenticate(request, username=username, password=password)
        if user is None:
            form.add_error(None, "Invalid username or password.")
        else:
            actual_role = _get_user_role(user)
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
    role = _get_user_role(request.user)
    if role is None:
        return redirect("login")

    return redirect(_get_dashboard_url(role))


def _render_role_dashboard(request, role, title):
    user_role = _get_user_role(request.user)
    if user_role != role:
        return HttpResponseForbidden("You do not have permission to access this page.")

    return render(
        request,
        "users/dashboard.html",
        {"page_title": title, "role": role, "user": request.user},
    )


def _handle_student_enrollment(request, student):
    action = request.POST.get("action")
    course_id = request.POST.get("course_id")

    if action not in {"enroll", "withdraw"} or not course_id:
        messages.error(request, "The submitted action is invalid.")
        return

    course = get_object_or_404(Course, pk=course_id)

    if action == "enroll":
        if Enrollment.objects.filter(student=student, course=course).exists():
            messages.warning(request, "You are already enrolled in this course.")
            return

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
    if _get_user_role(request.user) != "student":
        return HttpResponseForbidden("You do not have permission to access this page.")

    student = get_object_or_404(Student, user=request.user)

    if request.method == "POST":
        _handle_student_enrollment(request, student)
        active_tab = request.POST.get("tab", "courses")
        return redirect(f"{request.path}?tab={active_tab}")

    active_tab = request.GET.get("tab", "courses")
    if active_tab not in {"courses", "enrolled"}:
        active_tab = "courses"

    all_courses = Course.objects.select_related("teacher__user").all().order_by("id")
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
    return _render_role_dashboard(request, "teacher", "Teacher Dashboard")


@login_required
def admin_dashboard(request):
    return _render_role_dashboard(request, "admin", "Admin Dashboard")
