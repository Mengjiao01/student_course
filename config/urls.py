"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

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
    path("admin-page/", views.admin_dashboard, name="admin_dashboard"),
    path(
        "api/enrollments/",
        enrollment_views.create_enrollment,
        name="create_enrollment",
    ),

]
