from django.contrib import admin

from .models import (
    Classroom,
    Subject,
    TeachingAssignment,
    GradeScheme,
    AcademicScheme,
    AcademicSchemeRule,
)


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "grade_level",
        "school",
        "academic_year",
        "lead_teacher",
    )

    list_filter = (
        "school",
        "academic_year",
        "grade_level",
    )

    search_fields = (
        "name",
        "school__name",
        "lead_teacher__username",
        "lead_teacher__first_name",
        "lead_teacher__last_name",
    )


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "school",
    )

    list_filter = (
        "school",
    )

    search_fields = (
        "name",
        "code",
        "school__name",
    )


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "teacher",
        "classroom",
        "subject",
        "school",
    )

    list_filter = (
        "school",
        "subject",
        "classroom",
    )

    search_fields = (
        "teacher__username",
        "teacher__first_name",
        "teacher__last_name",
        "classroom__name",
        "subject__name",
    )


@admin.register(GradeScheme)
class GradeSchemeAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "assessment_type",
        "max_count",
        "weight",
        "school",
    )

    list_filter = (
        "school",
        "subject",
        "assessment_type",
    )

    search_fields = (
        "subject__name",
        "school__name",
    )



@admin.register(AcademicScheme)
class AcademicSchemeAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "school",
    ]

    list_filter = [
        "school",
    ]

    search_fields = [
        "name",
        "description",
    ]

    filter_horizontal = [
        "classrooms",
        "subjects",
    ]


@admin.register(AcademicSchemeRule)
class AcademicSchemeRuleAdmin(admin.ModelAdmin):
    list_display = [
        "scheme",
        "assessment_type",
        "max_count",
        "weight",
        "school",
    ]

    list_filter = [
        "assessment_type",
        "school",
    ]

    search_fields = [
        "scheme__name",
    ]