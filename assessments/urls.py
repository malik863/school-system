from django.urls import path

from . import views


app_name = "assessments"



urlpatterns = [
    path(
        "",
        views.assessment_list,
        name="list",
    ),
    path(
        "create/",
        views.assessment_create,
        name="create",
    ),
    path(
        "<int:pk>/",
        views.assessment_detail,
        name="detail",
    ),
    path(
        "<int:pk>/edit/",
        views.assessment_edit,
        name="edit",
    ),
    path(
        "<int:pk>/delete/",
        views.assessment_delete,
        name="delete",
    ),
    path(
        "<int:pk>/grades/",
        views.assessment_grades,
        name="grades",
    ),
]