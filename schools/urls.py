from django.urls import path,include

from . import views


from . import views
from academics import views as academic_views
from assessments import views as assessment_views


app_name = "manager"

urlpatterns = [
    path("", views.manager_dashboard, name="dashboard"),

    # Teachers
    path("teachers/", views.teacher_list, name="teacher_list"),
    path("teachers/add/", views.teacher_create, name="teacher_add"),
    path("teachers/<int:pk>/edit/", views.teacher_edit, name="teacher_edit"),
    path("teachers/<int:pk>/toggle-active/", views.teacher_toggle_active, name="teacher_toggle_active"),
    path("teachers/<int:pk>/delete/", views.teacher_delete, name="teacher_delete"),

    # Classes
    path("classes/", views.class_list, name="class_list"),
    path("classes/add/", views.class_create, name="class_add"),
    path("classes/<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("classes/<int:pk>/delete/", views.class_delete, name="class_delete"),

    # Subjects
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/add/", views.subject_create, name="subject_add"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/delete/", views.subject_delete, name="subject_delete"),

    # Students
    path("students/", views.student_list, name="student_list"),
    path("students/add/", views.student_create, name="student_add"),
    path("students/<int:pk>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:pk>/toggle-active/", views.student_toggle_active, name="student_toggle_active"),
    path("students/<int:pk>/delete/", views.student_delete, name="student_delete"),

    # Academic years
    path("academic/", views.academic_year_list, name="academic_year_list"),
    path("academic/year/add/", views.academic_year_create, name="academic_year_add"),
    path("academic/year/<int:pk>/edit/", views.academic_year_edit, name="academic_year_edit"),
    path("academic/year/<int:pk>/delete/", views.academic_year_delete, name="academic_year_delete"),

    # Terms
    path("academic/term/add/", views.term_create, name="term_add"),
    path("academic/term/<int:pk>/edit/", views.term_edit, name="term_edit"),
    path("academic/term/<int:pk>/delete/", views.term_delete, name="term_delete"),

        # Teaching Assignments
    path(
        "assignments/",
        academic_views.teaching_assignment_list,
        name="teaching_assignment_list",
    ),
    path(
        "assignments/add/",
        academic_views.teaching_assignment_create,
        name="teaching_assignment_add",
    ),
    path(
        "assignments/<int:pk>/edit/",
        academic_views.teaching_assignment_edit,
        name="teaching_assignment_edit",
    ),
    path(
        "assignments/<int:pk>/delete/",
        academic_views.teaching_assignment_delete,
        name="teaching_assignment_delete",
    ),
    # Grade Schemes
    path(
        "grade-schemes/",
        academic_views.grade_scheme_list,
        name="grade_scheme_list",
    ),
    path(
        "grade-schemes/add/",
        academic_views.grade_scheme_create,
        name="grade_scheme_add",
    ),
    path(
        "grade-schemes/<int:pk>/edit/",
        academic_views.grade_scheme_edit,
        name="grade_scheme_edit",
    ),
    path(
        "grade-schemes/<int:pk>/delete/",
        academic_views.grade_scheme_delete,
        name="grade_scheme_delete",
    ),


    path(
        "classroom-subjects/",
        academic_views.classroom_subject_list,
        name="classroom_subject_list",
    ),

    path(
        "classroom-subjects/add/",
        academic_views.classroom_subject_create,
        name="classroom_subject_add",
    ),

    path(
        "classroom-subjects/<int:pk>/delete/",
        academic_views.classroom_subject_delete,
        name="classroom_subject_delete",
    ),


    # =========================================================
    # ACADEMIC SCHEMES
    # =========================================================

    path(
        "academic-schemes/",
        academic_views.academic_scheme_list,
        name="academic_scheme_list",
    ),

    path(
        "academic-schemes/add/",
        academic_views.academic_scheme_create,
        name="academic_scheme_add",
    ),

    path(
        "academic-schemes/<int:pk>/edit/",
        academic_views.academic_scheme_edit,
        name="academic_scheme_edit",
    ),

    path(
        "academic-schemes/<int:pk>/delete/",
        academic_views.academic_scheme_delete,
        name="academic_scheme_delete",
    ),

    path(
        "academic-schemes/<int:scheme_pk>/rules/add/",
        academic_views.academic_scheme_rule_create,
        name="academic_scheme_rule_add",
    ),

    path(
        "academic-schemes/rules/<int:pk>/edit/",
        academic_views.academic_scheme_rule_edit,
        name="academic_scheme_rule_edit",
    ),

    path(
        "academic-schemes/rules/<int:pk>/delete/",
        academic_views.academic_scheme_rule_delete,
        name="academic_scheme_rule_delete",
    ),


]
