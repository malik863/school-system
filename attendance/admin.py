from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "classroom",
        "term",
        "date",
        "status",
        "recorded_by",
        "school",
    )

    list_filter = (
        "school",
        "status",
        "date",
        "term",
        "classroom",
    )

    search_fields = (
        "student__user__first_name",
        "student__user__last_name",
        "student__user__username",
        "classroom__name",
    )