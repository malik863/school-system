

from django.urls import path,include

from . import views
from attendance import views as attendance_views
from assessments import views as assessment_views

app_name = "teacher"


urlpatterns = [
    path(
        "",
        views.teacher_dashboard,
        name="dashboard",
    ),

    path(
        "assignments/",
        views.teacher_assignments,
        name="assignments",
    ),
    path(
        "attendance/",
        attendance_views.teacher_attendance,
        name="attendance",
    ),

    path(
    "assessments/",
    include("assessments.urls"),
    ),


    
    path(
    "assessments/",
    assessment_views.assessment_list,
    name="assessment_list",
),
    path(
        "assessments/create/",
        assessment_views.assessment_create,
        name="assessment_create",
    ),
    path(
        "assessments/<int:pk>/",
        assessment_views.assessment_detail,
        name="assessment_detail",
    ),
    path(
        "assessments/<int:pk>/edit/",
        assessment_views.assessment_edit,
        name="assessment_edit",
    ),
    path(
        "assessments/<int:pk>/delete/",
        assessment_views.assessment_delete,
        name="assessment_delete",
    ),
    path(
        "assessments/<int:pk>/grades/",
        assessment_views.assessment_grades,
        name="assessment_grades",
    ),




    path(
    "classes/",
    views.teacher_classes,
    name="classes",
    ),

    path(
        "classes/<int:pk>/",
        views.teacher_class_detail,
        name="class_detail",
    ),

    path(
        "subjects/",
        views.teacher_subjects,
        name="subjects",
    ),

    path(
        "subjects/<int:pk>/",
        views.teacher_subject_detail,
        name="subject_detail",
    ),

    path(
    "students/<int:student_id>/",
    views.teacher_student_detail,
    name="student_detail",
    ),

    path(
        "students/<int:student_id>/subject/<int:assignment_id>/",
        views.teacher_student_subject_detail,
        name="student_subject_detail",
    ),





]