from django.contrib import admin

from .models import Assessment, Grade


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "assessment_type",
        "school",
        "classroom",
        "subject",
        "term",
        "max_score",
        "date",
        "created_by",
    )

    list_filter = (
        "school",
        "assessment_type",
        "term",
        "subject",
        "classroom",
    )

    search_fields = (
        "title",
        "subject__name",
        "classroom__name",
        "school__name",
    )


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "assessment",
        "score",
        "school",
        "recorded_by",
        "recorded_at",
    )

    list_filter = (
        "school",
        "assessment__assessment_type",
        "assessment__term",
        "assessment__subject",
        "assessment__classroom",
    )

    search_fields = (
        "student__user__first_name",
        "student__user__last_name",
        "student__user__username",
        "assessment__title",
    )