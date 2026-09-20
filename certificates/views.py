from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from schools.decorators import school_admin_required

from .forms import CertificateTemplateForm
from .models import CertificateTemplate, CertificateField

import json
from PIL import Image

from django.contrib.auth.decorators import login_required

from academics.models import Classroom, ClassroomSubject
from assessments.models import Assessment

from students.models import StudentProfile
from assessments.models import Grade

from io import BytesIO

from django.http import FileResponse
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from django.http import FileResponse, HttpResponse

import arabic_reshaper

from bidi.algorithm import get_display

from django.conf import settings

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont




def get_student_certificate_data(
    student,
    classroom,
    assessments,
    school,
):
    grades = Grade.objects.filter(
        school=school,
        student=student,
        assessment__in=assessments,
    ).select_related("assessment")

    total_score = sum(
        grade.score
        for grade in grades
    )

    total_max_score = sum(
        grade.assessment.max_score
        for grade in grades
    )

    if total_max_score > 0:
        percentage = (
            total_score / total_max_score
        ) * 100
    else:
        percentage = 0

    if percentage >= 50:
        result = "Pass"
    else:
        result = "Fail"

    return {
        "student_name": str(student),
        "student_id": student.student_number or str(student.pk),
        "class_name": classroom.name,
        "academic_year": classroom.academic_year.name,
        "total": total_score,
        "percentage": f"{percentage:.2f}%",
        "result": result,
        "date":None

    }



ARABIC_FONT_PATH = r"C:\Windows\Fonts\arial.ttf"

pdfmetrics.registerFont(
    TTFont(
        "ArabicFont",
        ARABIC_FONT_PATH,
    )
)
def generate_certificate_pdf(
    template,
    student,
    classroom,
    assessments,
    school,
):
    certificate_data = get_student_certificate_data(
        student=student,
        classroom=classroom,
        assessments=assessments,
        school=school,
    )

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            template.width,
            template.height,
        ),
    )

    # Draw certificate background
    background = ImageReader(
        template.background.path
    )

    pdf.drawImage(
        background,
        0,
        0,
        width=template.width,
        height=template.height,
        preserveAspectRatio=False,
        mask="auto",
    )

    # Draw configured fields
    for field in template.fields.all():

        value = certificate_data.get(
            field.field_type,
            "",
        )

        if value is None:
            value = ""

        value = str(value)


        if any(
            "\u0600" <= char <= "\u06FF"
            for char in value
        ):
            value = get_display(
                arabic_reshaper.reshape(value)
            )

        # Font
        font_name = "ArabicFont"

        pdf.setFont(
            font_name,
            field.font_size,
        )
        # Field position
        x = field.x
        y = template.height - field.y - field.height

        # Alignment
        text_width = stringWidth(
            value,
            font_name,
            field.font_size,
        )

        if field.alignment == "center":
            text_x = x + (field.width - text_width) / 2

        elif field.alignment == "right":
            text_x = x + field.width - text_width

        else:
            text_x = x

        # Vertical center
        text_y = y + (
            field.height - field.font_size
        ) / 2

        pdf.drawString(
            text_x,
            text_y,
            value,
        )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer
@login_required
def test_certificate_pdf(request, student_id, template_id):
    school = request.user.school

    student = get_object_or_404(
        StudentProfile,
        id=student_id,
        school=school,
    )

    classroom = student.classroom

    template = get_object_or_404(
        CertificateTemplate,
        id=template_id,
        school=school,
        is_active=True,
    )

    assessments = Assessment.objects.filter(
        school=school,
        classroom=classroom,
    )

    pdf_buffer = generate_certificate_pdf(
        template=template,
        student=student,
        classroom=classroom,
        assessments=assessments,
        school=school,
    )

    return FileResponse(
        pdf_buffer,
        as_attachment=False,
        filename=f"certificate_{student.pk}.pdf",
        content_type="application/pdf",
    )


def generate_classroom_certificates_pdf(
    template,
    students,
    classroom,
    assessments,
    school,
):
    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            template.width,
            template.height,
        ),
    )

    for student in students:

        certificate_data = get_student_certificate_data(
            student=student,
            classroom=classroom,
            assessments=assessments,
            school=school,
        )

        background = ImageReader(
            template.background.path
        )

        pdf.drawImage(
            background,
            0,
            0,
            width=template.width,
            height=template.height,
            preserveAspectRatio=False,
            mask="auto",
        )

        for field in template.fields.all():

            value = certificate_data.get(
                field.field_type,
                "",
            )

            if value is None:
                value = ""

            value = str(value)

            if any(
                "\u0600" <= char <= "\u06FF"
                for char in value
            ):
                value = get_display(
                    arabic_reshaper.reshape(value)
                )

            font_name = "ArabicFont"

            pdf.setFont(
                font_name,
                field.font_size,
            )

            x = field.x

            y = (
                template.height
                - field.y
                - field.height
            )

            text_width = stringWidth(
                value,
                font_name,
                field.font_size,
            )

            if field.alignment == "center":
                text_x = (
                    x
                    + (field.width - text_width) / 2
                )

            elif field.alignment == "right":
                text_x = (
                    x
                    + field.width
                    - text_width
                )

            else:
                text_x = x

            text_y = y + (
                field.height - field.font_size
            ) / 2

            pdf.drawString(
                text_x,
                text_y,
                value,
            )

        pdf.showPage()

    pdf.save()

    buffer.seek(0)

    return buffer



@school_admin_required
def certificate_template_list(request):
    templates = CertificateTemplate.objects.filter(
        school=request.user.school
    ).order_by("-created_at")

    return render(
        request,
        "certificates/template_list.html",
        {
            "templates": templates,
        },
    )


@school_admin_required
def certificate_template_create(request):
    if request.method == "POST":
        form = CertificateTemplateForm(request.POST, request.FILES)

        if form.is_valid():
            template = form.save(commit=False)

            template.school = request.user.school

            image = form.cleaned_data["background"]

            with Image.open(image) as img:
                template.width = img.width
                template.height = img.height

            template.save()

            messages.success(
                request,
                "تم إضافة قالب الشهادة بنجاح."
            )

            return redirect(
                "certificates:template_list"
            )

    else:
        form = CertificateTemplateForm()

    return render(
        request,
        "certificates/template_form.html",
        {
            "form": form,
            "title": "إضافة قالب شهادة",
        },
    )


@school_admin_required
def certificate_template_delete(request, pk):
    template = get_object_or_404(
        CertificateTemplate,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        template.delete()

        messages.success(
            request,
            "تم حذف قالب الشهادة بنجاح."
        )

        return redirect("certificates:template_list")

    return render(
        request,
        "certificates/template_confirm_delete.html",
        {
            "template": template,
        },
    )




@school_admin_required
def certificate_template_designer(request, pk):
    template = get_object_or_404(
        CertificateTemplate,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        fields_data = request.POST.get("fields_data", "[]")

        try:
            fields = json.loads(fields_data)
        except json.JSONDecodeError:
            messages.error(request, "بيانات التصميم غير صالحة.")
            return redirect(
                "certificates:template_designer",
                pk=template.pk,
            )

        allowed_types = {
            choice[0]
            for choice in CertificateField.FIELD_TYPES
        }

        existing_ids = set()

        for field_data in fields:
            field_id = field_data.get("id")
            field_type = field_data.get("field_type")

            if field_type not in allowed_types:
                continue

            data = {
                "field_type": field_type,
                "label": field_data.get("label", ""),
                "x": float(field_data.get("x", 0)),
                "y": float(field_data.get("y", 0)),
                "width": float(field_data.get("width", 500)),
                "height": float(field_data.get("height", 100)),
                "font_size": int(field_data.get("font_size", 40)),
                "alignment": field_data.get("alignment", "center"),
                "font_name": field_data.get("font_name", "Arial"),
                "is_bold": bool(field_data.get("is_bold", False)),
            }

            if field_id:
                try:
                    certificate_field = CertificateField.objects.get(
                        id=field_id,
                        template=template,
                    )

                    for key, value in data.items():
                        setattr(certificate_field, key, value)

                    certificate_field.save()
                    existing_ids.add(certificate_field.id)

                except CertificateField.DoesNotExist:
                    pass

            else:
                certificate_field = CertificateField.objects.create(
                    template=template,
                    **data,
                )

                existing_ids.add(certificate_field.id)

        CertificateField.objects.filter(
            template=template
        ).exclude(
            id__in=existing_ids
        ).delete()

        messages.success(request, "تم حفظ تصميم الشهادة بنجاح.")

        return redirect(
            "certificates:template_designer",
            pk=template.pk,
        )

    fields = template.fields.all()

    return render(
        request,
        "certificates/template_designer.html",
        {
            "template": template,
            "fields": fields,
            "field_types": CertificateField.FIELD_TYPES,
        },
    )

@school_admin_required
def certificate_generation(request):
    school = request.user.school

    classrooms = Classroom.objects.filter(
        school=school
    )

    templates = CertificateTemplate.objects.filter(
        school=school,
        is_active=True
    )

    if request.method == "POST":
        classroom_id = request.POST.get("classroom")
        template_id = request.POST.get("template")

        classroom = get_object_or_404(
            Classroom,
            id=classroom_id,
            school=school,
        )

        template = get_object_or_404(
            CertificateTemplate,
            id=template_id,
            school=school,
            is_active=True,
        )

        # ---------------------------------------------------------
        # Students
        # ---------------------------------------------------------

        students = StudentProfile.objects.filter(
            school=school,
            classroom=classroom,
            is_active=True,
        )

        student_count = students.count()

        if student_count == 0:
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates because "
                        "this classroom has no active students."
                    ),
                },
            )

        # ---------------------------------------------------------
        # Academic scheme
        # ---------------------------------------------------------

        academic_scheme = classroom.academic_schemes.first()

        if not academic_scheme:
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates because "
                        "this classroom has no academic scheme assigned."
                    ),
                },
            )

        # ---------------------------------------------------------
        # Required subjects
        # ---------------------------------------------------------

        classroom_subjects = ClassroomSubject.objects.filter(
            school=school,
            classroom=classroom,
        ).select_related("subject")

        if not classroom_subjects.exists():
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates because "
                        "this classroom has no subjects assigned."
                    ),
                },
            )

        # Only subjects that belong to the academic scheme
        scheme_subject_ids = set(
            academic_scheme.subjects.values_list(
                "id",
                flat=True
            )
        )

        required_subjects = [
            classroom_subject
            for classroom_subject in classroom_subjects
            if classroom_subject.subject_id in scheme_subject_ids
        ]

        if not required_subjects:
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates because "
                        "no classroom subjects belong to the assigned "
                        "academic scheme."
                    ),
                },
            )

        # ---------------------------------------------------------
        # Academic scheme rules
        # ---------------------------------------------------------

        rules = academic_scheme.rules.all()

        if not rules.exists():
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates because "
                        "the academic scheme has no assessment rules."
                    ),
                },
            )

        # ---------------------------------------------------------
        # Check required assessments
        # ---------------------------------------------------------

        missing_assessments = []

        for classroom_subject in required_subjects:
            subject = classroom_subject.subject

            for rule in rules:
                actual_count = Assessment.objects.filter(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                    assessment_type=rule.assessment_type,
                ).count()

                if actual_count < rule.max_count:
                    missing_assessments.append(
                        f"{subject.name}: "
                        f"{rule.get_assessment_type_display()} "
                        f"({actual_count}/{rule.max_count})"
                    )

        if missing_assessments:
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates yet. "
                        "The following required assessments are missing: "
                        + ", ".join(missing_assessments)
                    ),
                },
            )

        # ---------------------------------------------------------
        # Check grades
        # ---------------------------------------------------------

        missing_grades = []

        for classroom_subject in required_subjects:
            subject = classroom_subject.subject

            for rule in rules:
                assessments = Assessment.objects.filter(
                    school=school,
                    classroom=classroom,
                    subject=subject,
                    assessment_type=rule.assessment_type,
                )

                # Only the required number of assessments matter.
                assessments = assessments.order_by("date", "id")[
                    :rule.max_count
                ]

                for assessment in assessments:
                    graded_students = Grade.objects.filter(
                        school=school,
                        assessment=assessment,
                        student__in=students,
                    ).values_list(
                        "student_id",
                        flat=True
                    )

                    graded_student_ids = set(graded_students)

                    for student in students:
                        if student.id not in graded_student_ids:
                            missing_grades.append(
                                f"{student} - "
                                f"{subject.name} - "
                                f"{assessment.title}"
                            )

        if missing_grades:
            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms": classrooms,
                    "templates": templates,
                    "error": (
                        "Cannot generate certificates yet. "
                        "Some students are missing grades: "
                        + ", ".join(missing_grades)
                    ),
                },
            )

        # ---------------------------------------------------------
        # Everything is complete
        # ---------------------------------------------------------

        # Get all assessments that belong to this classroom.
        # The completion checks above already verified that the
        # required assessments and grades are complete.
        assessments = Assessment.objects.filter(
            school=school,
            classroom=classroom,
        ).order_by("date", "id")

        # Generate the PDF for all students in the classroom.
        pdf_buffer = generate_classroom_certificates_pdf(
            template=template,
            students=students,
            classroom=classroom,
            assessments=assessments,
            school=school,
        )

        # Return the generated PDF as a download.
        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=f"certificates_{classroom.name}.pdf",
            content_type="application/pdf",
        )

    # -------------------------------------------------------------
    # GET
    # -------------------------------------------------------------

    return render(
        request,
        "certificates/certificate_generation.html",
        {
            "classrooms": classrooms,
            "templates": templates,
        },
    )
def get_student_certificate_data(
    student,
    classroom,
    assessments,
    school,
):
    grades = Grade.objects.filter(
        school=school,
        student=student,
        assessment__in=assessments,
    ).select_related("assessment")

    total_score = sum(
        grade.score
        for grade in grades
    )

    total_max_score = sum(
        grade.assessment.max_score
        for grade in grades
    )

    if total_max_score > 0:
        percentage = (
            total_score / total_max_score
        ) * 100
    else:
        percentage = 0

    if percentage >= 50:
        result = "Pass"
    else:
        result = "Fail"

    return {
        "student_name": str(student),
        "student_id": student.student_number,
        "class_name": classroom.name,
        "academic_year": classroom.academic_year.name,
        "total": total_score,
        "percentage": f"{percentage:.2f}%",
        "result": result,
        "date": None,
    }
    