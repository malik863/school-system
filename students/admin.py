from django.contrib import admin

from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "school",
        "classroom",
        "student_number",
        "national_id",
        "parent_phone",
        "is_active",
    )

    list_filter = (
        "school",
        "classroom",
        "is_active",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "student_number",
        "national_id",
    )