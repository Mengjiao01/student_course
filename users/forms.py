from django import forms
from django.core.exceptions import ValidationError

from courses.models import Course
from users.models import Teacher


class LoginForm(forms.Form):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("teacher", "Teacher"),
        ("admin", "Admin"),
    ]

    username = forms.CharField(
        label="Username",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your username",
                "autocomplete": "off",
                "autocapitalize": "none",
                "spellcheck": "false",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "new-password",
            }
        ),
    )
    role = forms.ChoiceField(
        label="Role",
        choices=ROLE_CHOICES,
        widget=forms.Select(
            attrs={"class": "form-select", "autocomplete": "off"}
        ),
    )


class AdminCourseForm(forms.ModelForm):
    teacher_staff_ids = forms.CharField(
        label="Teacher IDs",
        required=False,
        help_text="Separate multiple teacher IDs with commas.",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "For example: T001,T002",
            }
        ),
    )

    class Meta:
        model = Course
        fields = [
            "course_name",
            "course_code",
            "credits",
            "schedule",
            "location",
            "start_date",
            "end_date",
            "delivery_mode",
            "description",
        ]
        widgets = {
            "course_name": forms.TextInput(attrs={"class": "form-control"}),
            "course_code": forms.TextInput(attrs={"class": "form-control"}),
            "credits": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "schedule": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "For example: Monday 08:00-10:00"}
            ),
            "location": forms.TextInput(attrs={"class": "form-control"}),
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "YYYY-MM-DD",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                },
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "text",
                    "placeholder": "YYYY-MM-DD",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                },
            ),
            "delivery_mode": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
        labels = {
            "course_name": "Course Name",
            "course_code": "Course ID",
            "credits": "Credits",
            "schedule": "Class Schedule",
            "location": "Location",
            "start_date": "Term Start Date",
            "end_date": "Term End Date",
            "delivery_mode": "Class Mode",
            "description": "Course Description",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].input_formats = ["%Y-%m-%d"]
        if self.instance.pk:
            self.fields["teacher_staff_ids"].initial = ",".join(
                teacher.staff_id for teacher in self.instance.teacher_list()
            )

    def clean_teacher_staff_ids(self):
        raw_value = self.cleaned_data["teacher_staff_ids"]
        staff_ids = [staff_id.strip() for staff_id in raw_value.split(",") if staff_id.strip()]
        if not staff_ids:
            return []

        teachers = list(Teacher.objects.filter(staff_id__in=staff_ids).select_related("user"))
        teacher_map = {teacher.staff_id: teacher for teacher in teachers}
        missing_ids = [staff_id for staff_id in staff_ids if staff_id not in teacher_map]
        if missing_ids:
            raise ValidationError("The following teacher IDs do not exist: %s" % ", ".join(missing_ids))

        return [teacher_map[staff_id] for staff_id in staff_ids]

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise ValidationError("The term start date cannot be later than the end date.")
        return cleaned_data

    def save(self, commit=True):
        course = super().save(commit=False)
        if not course.capacity:
            course.capacity = 50

        teachers = self.cleaned_data.get("teacher_staff_ids", [])
        course.teacher = teachers[0] if teachers else None

        if commit:
            course.save()
            course.teachers.set(teachers)
        else:
            self._pending_teachers = teachers

        return course

    def save_m2m(self):
        super().save_m2m()
        if hasattr(self, "_pending_teachers"):
            self.instance.teachers.set(self._pending_teachers)

