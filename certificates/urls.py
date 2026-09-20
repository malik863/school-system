
from django.urls import path

from . import views


app_name = "certificates"


urlpatterns = [
    path(
        "templates/",
        views.certificate_template_list,
        name="template_list",
    ),

    path(
        "templates/add/",
        views.certificate_template_create,
        name="template_create",
    ),

    path(
        "templates/<int:pk>/delete/",
        views.certificate_template_delete,
        name="template_delete",
    ),
    path(
    "templates/<int:pk>/designer/",
    views.certificate_template_designer,
    name="template_designer",
),
    path(
        "generate/",
        views.certificate_generation,
        name="certificate_generation",
    ),

    path(
        "test-pdf/<int:student_id>/<int:template_id>/",
        views.test_certificate_pdf,
        name="test_certificate_pdf",
    ),
]