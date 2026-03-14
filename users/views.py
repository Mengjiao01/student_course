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

# Role to dashboard mapping
def _get_dashboard_url(role):
    role_to_url = {
        "student": "student_dashboard",
        "teacher": "teacher_dashboard",
        "admin": "admin_dashboard",
    }
    return role_to_url[role]


def _admin_only(request):
    if get_user_role(request.user) != "admin":
        return HttpResponseForbidden("You do not have permission to access this page.")
    return None


def _teacher_detail_payload(teacher):
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
    return Course.objects.select_related("teacher__user").prefetch_related("teachers__user")


def _course_admin_queryset():
    return (
        Course.objects.select_related("teacher__user")
        .prefetch_related("teachers__user")
        .annotate(enrolled_total=Count("enrollment", distinct=True))
    )


def _get_login_user(selected_role, login_id):
    #Role-specific ID lookup
    if selected_role == "student":
        student = Student.objects.select_related("user").filter(student_id=login_id).first()
        return student.user if student else None

    if selected_role == "teacher":
        teacher = Teacher.objects.select_related("user").filter(staff_id=login_id).first()
        return teacher.user if teacher else None

    profile = Profile.objects.select_related("user").filter(role="admin", admin_id=login_id).first()
    return profile.user if profile else None


def _get_login_user_by_any_id(login_id):
    #Any-role ID lookup
    student = Student.objects.select_related("user").filter(student_id=login_id).first()
    if student:
        return student.user

    teacher = Teacher.objects.select_related("user").filter(staff_id=login_id).first()
    if teacher:
        return teacher.user

    profile = Profile.objects.select_related("user").filter(admin_id=login_id).first()
    return profile.user if profile else None


@never_cache
@ensure_csrf_cookie
def login_view(request):
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        #Submitted credentials
        login_id = form.cleaned_data["login_id"].strip()
        password = form.cleaned_data["password"]
        selected_role = form.cleaned_data["role"]

        
        user = _get_login_user(selected_role, login_id)
        if user is not None:
            #cheak password
            if not user.check_password(password):
                form.add_error(None, "Invalid ID or password.")
            else:
                
                login(request, user)
                return redirect(_get_dashboard_url(selected_role))
        else:
            #role mismatch fallback
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
    #use one POST entry point for both enroll and withdraw actions
    action = request.POST.get("action")
    course_id = request.POST.get("course_id")

    if action not in {"enroll", "withdraw"} or not course_id:
        messages.error(request, "The submitted action is invalid.")
        return

    course = get_object_or_404(Course, pk=course_id)

    if action == "enroll":
        #prevent duplicate enrollments before checking remaining capacity
        if Enrollment.objects.filter(student=student, course=course).exists():
            messages.warning(request, "You are already enrolled in this course.")
            return

        if course.enrolled_count() >= course.capacity:
            messages.error(request, "This course is full and cannot accept more enrollments.")
            return

        Enrollment.objects.create(student=student, course=course)
        messages.success(request, "Enrollment successful.")
        return

    #remove the student's enrollment record for the selected course
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
        #redirect back to the current tab
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

    context = {
        "student": student,
        "active_tab": active_tab,
        "all_courses": all_courses,
        "enrolled_courses": enrolled_courses,
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

    sort_map = {
        "name": "course_name",
        "name_desc": "-course_name",
        "schedule": "schedule",
        "schedule_desc": "-schedule",
        "code": "course_code",
        "code_desc": "-course_code",
    }
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
    course = get_object_or_404(_teacher_course_queryset().distinct(), pk=course_id)
    if teacher not in course.teacher_list():
        raise Http404("Course not found.")

    query = request.GET.get("q", "").strip()

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
            "teacher": teacher,
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

    return render(request, "users/admin_dashboard.html", {"user": request.user, "admin_id": request.user.profile.admin_id})


@login_required
def admin_module_placeholder(request, module_name):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    module_labels = {
        "students": "Student Management",
        "teachers": "Teacher Management",
        "admins": "Administrator Management",
    }
    module_label = module_labels.get(module_name)
    if module_label is None:
        return redirect("admin_dashboard")

    return render(
        request,
        "users/admin_module_placeholder.html",
        {
            "module_label": module_label,
            "module_name": module_name,
        },
    )

#verify
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

    teachers = course.teacher_list()
    if teacher_query:
        lowered_query = teacher_query.lower()
        teachers = [
            teacher for teacher in teachers
            if lowered_query in teacher.staff_id.lower()
            or lowered_query in teacher.department.lower()
        ]
    teacher_page_obj = Paginator(teachers, 5).get_page(request.GET.get("teacher_page"))

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
    return JsonResponse(_teacher_detail_payload(teacher))


@login_required
def admin_student_detail_modal(request, student_id):
    forbidden_response = _admin_only(request)
    if forbidden_response is not None:
        return forbidden_response

    student = get_object_or_404(Student.objects.select_related("user"), pk=student_id)
    return JsonResponse(_student_detail_payload(student))

