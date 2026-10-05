from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    # Legacy manager URL kept for compatibility. The real manager area is /manager/.
    path("dashboard/manager/", views.manager_dashboard, name="manager_dashboard"),
    path("dashboard/teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("dashboard/student/", views.student_dashboard, name="student_dashboard"),
    path("classroom/<int:classroom_id>/enter-grades/", views.enter_grades, name="enter_grades"),
    path("student/<int:student_id>/report-card/", views.student_report_card, name="student_report_card"),
]
