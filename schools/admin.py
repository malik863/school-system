from django.contrib import admin

from .models import School, AcademicYear, Term


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "slug",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "slug",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "school",
        "start_date",
        "end_date",
        "is_current",
    )

    list_filter = (
        "school",
        "is_current",
    )

    search_fields = (
        "name",
        "school__name",
    )


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "school",
        "academic_year",
        "start_date",
        "end_date",
        "is_current",
        "is_closed",
    )

    list_filter = (
        "school",
        "academic_year",
        "is_current",
        "is_closed",
    )

    search_fields = (
        "name",
        "school__name",
        "academic_year__name",
    )

