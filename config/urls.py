"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from courses import views as course_views
from enrollments import views as enrollment_views
from users import views

urlpatterns = [
    path("", views.dashboard_redirect, name="home"),
    path("admin/", admin.site.urls),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path(
        "teacher/courses/<int:course_id>/students/",
        views.teacher_course_students,
        name="teacher_course_students",
    ),
    path("admin-page/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "api/student/courses/",
        course_views.student_course_list,
        name="student_course_list",
    ),
    path(
        "api/student/courses/<int:course_id>/",
        course_views.student_course_detail,
        name="student_course_detail",
    ),
    path(
        "api/student/enrolled-courses/",
        course_views.student_enrolled_course_list,
        name="student_enrolled_course_list",
    ),
    path(
        "api/enrollments/",
        enrollment_views.create_enrollment,
        name="create_enrollment",
    ),
]
