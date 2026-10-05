import json
import os
from decimal import Decimal

from io import BytesIO

from PIL import Image

import arabic_reshaper
from bidi.algorithm import get_display

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from academics.models import Classroom, ClassroomSubject, Subject, AcademicSchemeRule
from academics.grade_calculator import (
    student_term_result, student_year_result, attendance_percentage, attendance_grade_result,
)
from assessments.models import Assessment, Grade
from schools.decorators import school_admin_required
from schools.models import AcademicYear, Term
from students.models import StudentProfile, StudentEnrollment

from .forms import CertificateTemplateForm
from .models import CertificateField, CertificateTemplate


# ============================================================
# CERTIFICATE FONT SETUP
# ============================================================

CERTIFICATE_FONT_DIR = os.path.join(
    settings.BASE_DIR,
    "certificates",
    "fonts",
)


CERTIFICATE_FONTS = {
    "Amiri": {
        "regular": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Amiri-Regular.ttf",
        ),
        "bold": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Amiri-Bold.ttf",
        ),
    },

    "Cairo": {
        "regular": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Cairo-Regular.ttf",
        ),
        "bold": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Cairo-Bold.ttf",
        ),
    },

    "Tajawal": {
        "regular": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Tajawal-Regular.ttf",
        ),
        "bold": os.path.join(
            CERTIFICATE_FONT_DIR,
            "Tajawal-Bold.ttf",
        ),
    },

    "NotoArabic": {
        "regular": os.path.join(
            CERTIFICATE_FONT_DIR,
            "NotoArabic-Regular.ttf",
        ),
        "bold": os.path.join(
            CERTIFICATE_FONT_DIR,
            "NotoArabic-Bold.ttf",
        ),
    },
}


# ============================================================
# REGISTER REPORTLAB FONTS
# ============================================================

def register_certificate_fonts():

    for font_family, font_files in CERTIFICATE_FONTS.items():

        regular_name = (
            f"{font_family}-Regular"
        )

        bold_name = (
            f"{font_family}-Bold"
        )

        if (
            regular_name
            not in pdfmetrics.getRegisteredFontNames()
        ):

            pdfmetrics.registerFont(
                TTFont(
                    regular_name,
                    font_files["regular"],
                )
            )

        if (
            bold_name
            not in pdfmetrics.getRegisteredFontNames()
        ):

            pdfmetrics.registerFont(
                TTFont(
                    bold_name,
                    font_files["bold"],
                )
            )


register_certificate_fonts()


# ============================================================
# STUDENT CERTIFICATE DATA
# ============================================================

def get_student_certificate_data(student, classroom, assessments, school, template=None):
    """Legacy certificate fields, resolved through the same central calculator."""
    if template is not None:
        terms = list(Term.objects.filter(
            school=school, academic_year=classroom.academic_year
        ).order_by("start_date", "id"))
        if template.period == CertificateTemplate.Period.ACADEMIC_YEAR:
            central = student_year_result(student, classroom.academic_year, classroom=classroom)
        else:
            index = 1 if template.period == CertificateTemplate.Period.TERM_2 else 0
            central = (student_term_result(student, terms[index], classroom=classroom)
                       if len(terms) > index else {"score": Decimal("0"), "max_score": Decimal("0"), "percentage": None})
        total_score = central["score"]
        total_max_score = central["max_score"]
        percentage = central["percentage"] or Decimal("0")
    else:
        grades = Grade.objects.filter(
            school=school, student=student, assessment__in=assessments
        ).select_related("assessment")
        total_score = sum((grade.score for grade in grades), Decimal("0"))
        total_max_score = sum((grade.assessment.max_score for grade in grades), Decimal("0"))
        percentage = (total_score / total_max_score * Decimal("100")) if total_max_score else Decimal("0")

    return {
        "student_name": str(student),
        "student_id": student.student_number or str(student.pk),
        "class_name": classroom.name,
        "academic_year": classroom.academic_year.name,
        "total": f"{total_score} / {total_max_score}" if total_max_score else total_score,
        "percentage": f"{percentage:.2f}%",
        "result": "Pass" if percentage >= Decimal("50") else "Fail",
        "date": None,
    }


def resolve_dynamic_certificate_field(field, student, classroom):
    """Resolve term/year and subject fields without storing calculated grades."""
    academic_year = classroom.academic_year
    subject = field.subject
    if field.field_type == "subject_name":
        return subject.name if subject else ""

    # Attendance fields follow the certificate template period.  They do not
    # depend on the school's current term and can therefore be used when
    # reprinting historical certificates.
    if field.field_type in {"attendance", "attendance_grade"}:
        terms = list(Term.objects.filter(
            school=student.school, academic_year=academic_year
        ).order_by("start_date", "id"))
        template_period = field.template.period
        if template_period == CertificateTemplate.Period.ACADEMIC_YEAR:
            term = None
        else:
            index = 1 if template_period == CertificateTemplate.Period.TERM_2 else 0
            if len(terms) <= index:
                return ""
            term = terms[index]

        if field.field_type == "attendance":
            pct = attendance_percentage(
                student, term=term, academic_year=(academic_year if term is None else None)
            )
            if pct is None:
                return ""
            shown = f"{pct:.2f}".rstrip("0").rstrip(".")
            return f"{shown}%"

        result = attendance_grade_result(
            student, classroom, term=term, academic_year=(academic_year if term is None else None)
        )
        if not result["max_score"]:
            return ""
        score = f'{result["score"]:.2f}'.rstrip("0").rstrip(".")
        maximum = f'{result["max_score"]:.2f}'.rstrip("0").rstrip(".")
        return f"{score} / {maximum}"

    if field.field_type not in {"period_total", "period_percentage", "subject_total", "subject_percentage"}:
        return None
    result = (student_term_result(student, field.term, subject=subject, classroom=classroom)
              if field.term_id else
              student_year_result(student, academic_year, subject=subject, classroom=classroom))
    if field.field_type.endswith("percentage"):
        value = result["percentage"]
        if value is None:
            return ""
        shown = f"{value:.2f}".rstrip("0").rstrip(".")
        return f"{shown}%"
    if not result["max_score"]:
        return ""
    score = f'{result["score"]:.2f}'.rstrip("0").rstrip(".")
    maximum = f'{result["max_score"]:.2f}'.rstrip("0").rstrip(".")
    return f"{score} / {maximum}"


# ============================================================
# PREPARE TEXT FOR PDF
# ============================================================

def prepare_certificate_text(value):

    if value is None:

        return ""

    value = str(value)

    has_arabic = any(
        "\u0600" <= char <= "\u06FF"
        for char in value
    )

    if has_arabic:

        value = get_display(
            arabic_reshaper.reshape(
                value
            )
        )

    return value


# ============================================================
# GET PDF FONT
# ============================================================

def get_certificate_font(field):

    font_family = getattr(
        field,
        "font_name",
        "Amiri",
    )

    # Old database values
    if font_family == "Arial":
        font_family = "Amiri"

    # Invalid/removed font
    if font_family not in CERTIFICATE_FONTS:
        font_family = "Amiri"

    is_bold = getattr(
        field,
        "is_bold",
        False,
    )

    if is_bold:

        return f"{font_family}-Bold"

    return f"{font_family}-Regular"


# ============================================================
# SET PDF FONT COLOR
# ============================================================

def set_certificate_field_color(
    pdf,
    field,
):

    color_value = getattr(
        field,
        "font_color",
        "#000000",
    )

    if not color_value:

        color_value = "#000000"

    try:

        pdf.setFillColor(
            HexColor(
                color_value
            )
        )

    except (
        ValueError,
        TypeError,
    ):

        pdf.setFillColor(
            HexColor(
                "#000000"
            )
        )


# ============================================================
# DRAW ONE CERTIFICATE FIELD
# ============================================================

def draw_certificate_field(
    pdf,
    template,
    field,
    value,
):

    value = prepare_certificate_text(
        value
    )

    font_name = get_certificate_font(
        field
    )

    font_size = field.font_size

    pdf.setFont(
        font_name,
        font_size,
    )

    set_certificate_field_color(
        pdf,
        field,
    )

    # Browser uses top-left coordinates.
    # PDF uses bottom-left coordinates.

    x = field.x

    y = (
        template.height
        - field.y
        - field.height
    )

    text_width = stringWidth(
        value,
        font_name,
        font_size,
    )

    if field.alignment == "center":

        text_x = (
            x
            + (
                field.width
                - text_width
            ) / 2
        )

    elif field.alignment == "right":

        text_x = (
            x
            + field.width
            - text_width
        )

    else:

        text_x = x

    text_y = (
        y
        + (
            field.height
            - font_size
        ) / 2
    )

    pdf.drawString(
        text_x,
        text_y,
        value,
    )


# ============================================================
# GENERATE ONE STUDENT CERTIFICATE
# ============================================================

def generate_certificate_pdf(
    template,
    student,
    classroom,
    assessments,
    school,
):

    certificate_data = (
        get_student_certificate_data(
            student=student,
            classroom=classroom,
            assessments=assessments,
            school=school,
        )
    )

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(
            template.width,
            template.height,
        ),
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

        dynamic_value = resolve_dynamic_certificate_field(field, student, classroom)
        value = (dynamic_value if dynamic_value is not None else
                 certificate_data.get(field.field_type, ""))

        draw_certificate_field(
            pdf=pdf,
            template=template,
            field=field,
            value=value,
        )

    pdf.showPage()
    pdf.save()

    buffer.seek(0)

    return buffer


# ============================================================
# TEST / PREVIEW SINGLE CERTIFICATE
# ============================================================

@school_admin_required
def test_certificate_pdf(
    request,
    student_id,
    template_id,
):

    school = request.user.school

    student = get_object_or_404(
        StudentProfile,
        id=student_id,
        school=school,
    )

    classroom = student.classroom
    requested_classroom_id = request.GET.get("classroom")
    if requested_classroom_id:
        enrollment = get_object_or_404(
            StudentEnrollment.objects.select_related("classroom"),
            school=school, student=student, classroom_id=requested_classroom_id,
        )
        classroom = enrollment.classroom

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


# ============================================================
# GENERATE CERTIFICATES FOR WHOLE CLASS
# ============================================================

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

    background = ImageReader(
        template.background.path
    )

    for student in students:

        certificate_data = (
            get_student_certificate_data(
                student=student,
                classroom=classroom,
                assessments=assessments,
                school=school,
                template=template,
            )
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

            dynamic_value = resolve_dynamic_certificate_field(field, student, classroom)
            value = (dynamic_value if dynamic_value is not None else
                     certificate_data.get(field.field_type, ""))

            draw_certificate_field(
                pdf=pdf,
                template=template,
                field=field,
                value=value,
            )

        pdf.showPage()

    pdf.save()

    buffer.seek(0)

    return buffer


# ============================================================
# CERTIFICATE TEMPLATE LIST
# ============================================================

@school_admin_required
def certificate_template_list(request):

    templates = (
        CertificateTemplate.objects
        .filter(
            school=request.user.school
        )
        .order_by(
            "-created_at"
        )
    )

    return render(
        request,
        "certificates/template_list.html",
        {
            "templates": templates,
        },
    )


# ============================================================
# CREATE CERTIFICATE TEMPLATE
# ============================================================

@school_admin_required
def certificate_template_create(request):

    if request.method == "POST":

        form = CertificateTemplateForm(
            request.POST,
            request.FILES,
        )

        form.fields["classroom"].queryset = Classroom.objects.filter(school=request.user.school).select_related("academic_year")

        if form.is_valid():

            template = form.save(
                commit=False
            )

            template.school = (
                request.user.school
            )

            image = (
                form.cleaned_data[
                    "background"
                ]
            )

            with Image.open(
                image
            ) as img:

                template.width = (
                    img.width
                )

                template.height = (
                    img.height
                )

            template.save()

            messages.success(
                request,
                "تم إضافة قالب الشهادة بنجاح.",
            )

            return redirect(
                "certificates:template_list"
            )

    else:

        form = CertificateTemplateForm()
        form.fields["classroom"].queryset = Classroom.objects.filter(school=request.user.school).select_related("academic_year")

    return render(
        request,
        "certificates/template_form.html",
        {
            "form":
                form,

            "title":
                "إضافة قالب شهادة",
        },
    )


# ============================================================
# EDIT CERTIFICATE TEMPLATE
# ============================================================
@school_admin_required
def certificate_template_edit(request, pk):
    template = get_object_or_404(CertificateTemplate, pk=pk, school=request.user.school)
    form = CertificateTemplateForm(
        request.POST or None, request.FILES or None, instance=template
    )
    form.fields["classroom"].queryset = Classroom.objects.filter(
        school=request.user.school
    ).select_related("academic_year")
    if request.method == "POST" and form.is_valid():
        updated = form.save(commit=False)
        updated.school = request.user.school
        if "background" in request.FILES:
            with Image.open(request.FILES["background"]) as img:
                updated.width, updated.height = img.width, img.height
        updated.save()
        messages.success(request, "تم تحديث إعدادات قالب الشهادة بنجاح.")
        return redirect("certificates:template_list")
    return render(request, "certificates/template_form.html", {
        "form": form, "title": "تعديل قالب الشهادة"
    })


# ============================================================
# DELETE CERTIFICATE TEMPLATE
# ============================================================

@school_admin_required
def certificate_template_delete(
    request,
    pk,
):

    template = get_object_or_404(
        CertificateTemplate,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":

        template.delete()

        messages.success(
            request,
            "تم حذف قالب الشهادة بنجاح.",
        )

        return redirect(
            "certificates:template_list"
        )

    return render(
        request,
        "certificates/template_confirm_delete.html",
        {
            "template":
                template,
        },
    )


# ============================================================
# CERTIFICATE DESIGNER
# ============================================================

@school_admin_required
def certificate_template_designer(
    request,
    pk,
):

    template = get_object_or_404(
        CertificateTemplate,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":

        fields_data = request.POST.get(
            "fields_data",
            "[]",
        )

        try:

            fields = json.loads(
                fields_data
            )

        except json.JSONDecodeError:

            messages.error(
                request,
                "بيانات التصميم غير صالحة.",
            )

            return redirect(
                "certificates:template_designer",
                pk=template.pk,
            )

        allowed_types = {
            choice[0]
            for choice in CertificateField.FIELD_TYPES
        }

        allowed_fonts = {
            "Amiri",
            "Cairo",
            "Tajawal",
            "NotoArabic",
        }

        existing_ids = set()

        for field_data in fields:

            field_id = field_data.get(
                "id"
            )

            field_type = field_data.get(
                "field_type"
            )

            if field_type not in allowed_types:
                continue

            font_name = field_data.get(
                "font_name",
                "Amiri",
            )

            if font_name not in allowed_fonts:
                font_name = "Amiri"

            data = {

                "field_type":
                    field_type,

                "label":
                    field_data.get(
                        "label",
                        "",
                    ),

                "x":
                    float(
                        field_data.get(
                            "x",
                            0,
                        )
                    ),

                "y":
                    float(
                        field_data.get(
                            "y",
                            0,
                        )
                    ),

                "width":
                    float(
                        field_data.get(
                            "width",
                            500,
                        )
                    ),

                "height":
                    float(
                        field_data.get(
                            "height",
                            100,
                        )
                    ),

                "font_size":
                    int(
                        field_data.get(
                            "font_size",
                            40,
                        )
                    ),

                "alignment":
                    field_data.get(
                        "alignment",
                        "center",
                    ),

                "font_name":
                    font_name,

                "font_color":
                    field_data.get(
                        "font_color",
                        "#000000",
                    ),

                "is_bold":
                    bool(
                        field_data.get(
                            "is_bold",
                            False,
                        )
                    ),

                "subject_id": field_data.get("subject_id") or None,
                "term_id": field_data.get("term_id") or None,
                "result_value": field_data.get("result_value", ""),
            }

            if field_id:

                try:

                    certificate_field = (
                        CertificateField.objects.get(
                            id=field_id,
                            template=template,
                        )
                    )

                    for key, value in data.items():

                        setattr(
                            certificate_field,
                            key,
                            value,
                        )

                    certificate_field.save()

                    existing_ids.add(
                        certificate_field.id
                    )

                except CertificateField.DoesNotExist:

                    pass

            else:

                certificate_field = (
                    CertificateField.objects.create(
                        template=template,
                        **data,
                    )
                )

                existing_ids.add(
                    certificate_field.id
                )

        CertificateField.objects.filter(
            template=template
        ).exclude(
            id__in=existing_ids
        ).delete()

        messages.success(
            request,
            "تم حفظ تصميم الشهادة بنجاح.",
        )

        return redirect(
            "certificates:template_designer",
            pk=template.pk,
        )

    fields = template.fields.all()
    designer_subjects = Subject.objects.filter(school=request.user.school)
    if template.classroom_id:
        designer_subjects = designer_subjects.filter(classroom_subjects__classroom=template.classroom).distinct()
    designer_terms = Term.objects.filter(
        school=request.user.school,
        academic_year=(template.classroom.academic_year if template.classroom_id else AcademicYear.objects.filter(school=request.user.school, is_current=True).first()),
    ).select_related("academic_year").order_by("start_date")

    return render(
        request,
        "certificates/template_designer.html",
        {
            "template":
                template,

            "fields":
                fields,

            "field_types": CertificateField.FIELD_TYPES,
            "subjects": designer_subjects.order_by("name"),
            "terms": designer_terms,
        },
    )


# ============================================================
# CERTIFICATE GENERATION PAGE
# ============================================================

@school_admin_required
def certificate_generation(request):

    school = request.user.school

    classrooms = Classroom.objects.filter(
        school=school
    )

    templates = CertificateTemplate.objects.filter(
        school=school,
        is_active=True,
    )

    if request.method == "POST":

        classroom_id = request.POST.get(
            "classroom"
        )

        template_id = request.POST.get(
            "template"
        )

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

        if template.classroom_id and template.classroom_id != classroom.id:
            return render(request, "certificates/certificate_generation.html", {
                "classrooms": classrooms, "templates": templates,
                "error": "هذا القالب مخصص لفصل مختلف. اختر القالب الخاص بهذا الفصل.",
            })

        # ====================================================
        # STUDENTS
        # ====================================================

        enrolled_ids = StudentEnrollment.objects.filter(
            school=school, classroom=classroom
        ).values_list("student_id", flat=True)
        students = StudentProfile.objects.filter(
            school=school, id__in=enrolled_ids, is_active=True,
        )

        student_count = students.count()

        if student_count == 0:

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates because "
                            "this classroom has no active students."
                        ),
                },
            )

        # ====================================================
        # ACADEMIC SCHEME
        # ====================================================

        academic_scheme = (
            classroom
            .academic_schemes
            .first()
        )

        if not academic_scheme:

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates because "
                            "this classroom has no academic scheme assigned."
                        ),
                },
            )

        # ====================================================
        # CLASSROOM SUBJECTS
        # ====================================================

        classroom_subjects = (
            ClassroomSubject.objects
            .filter(
                school=school,
                classroom=classroom,
            )
            .select_related(
                "subject"
            )
        )

        if not classroom_subjects.exists():

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates because "
                            "this classroom has no subjects assigned."
                        ),
                },
            )

        # ====================================================
        # SUBJECTS INCLUDED IN ACADEMIC SCHEME
        # ====================================================

        scheme_subject_ids = set(
            academic_scheme.subjects.values_list(
                "id",
                flat=True,
            )
        )

        required_subjects = [
            classroom_subject
            for classroom_subject in classroom_subjects
            if (
                classroom_subject.subject_id
                in scheme_subject_ids
            )
        ]

        if not required_subjects:

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates because "
                            "no classroom subjects belong to the assigned "
                            "academic scheme."
                        ),
                },
            )

        # ====================================================
        # ACADEMIC SCHEME RULES
        # ====================================================

        rules = academic_scheme.rules.all()

        if not rules.exists():

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates because "
                            "the academic scheme has no assessment rules."
                        ),
                },
            )

        # ====================================================
        # TERMS REQUIRED BY THIS TEMPLATE
        # ====================================================
        academic_year_terms = list(Term.objects.filter(
            school=school, academic_year=classroom.academic_year
        ).order_by("start_date", "id"))
        # The template period is the authority for certificate readiness.
        # It is intentionally independent from the school's current term and
        # from which result fields happen to be placed on the design.
        if template.period == CertificateTemplate.Period.ACADEMIC_YEAR:
            required_terms = academic_year_terms
        elif template.period == CertificateTemplate.Period.TERM_2:
            required_terms = academic_year_terms[1:2]
        else:
            required_terms = academic_year_terms[:1]

        if not required_terms:
            return render(request, "certificates/certificate_generation.html", {
                "classrooms": classrooms, "templates": templates,
                "error": "لا توجد فترة دراسية مطابقة لفترة هذا القالب في العام الدراسي المختار.",
            })

        # ====================================================
        # CHECK REQUIRED ASSESSMENTS
        # ====================================================

        missing_assessments = []

        for classroom_subject in required_subjects:
            subject = classroom_subject.subject
            for term in required_terms:
                for rule in rules:
                    if rule.assessment_type == AcademicSchemeRule.AssessmentType.ATTENDANCE:
                        continue
                    actual_count = Assessment.objects.filter(
                        school=school, classroom=classroom, subject=subject, term=term,
                        assessment_type=rule.assessment_type,
                    ).count()
                    if actual_count < rule.max_count:
                        missing_assessments.append(
                            f"{subject.name} - {term.name}: {rule.get_assessment_type_display()} "
                            f"({actual_count}/{rule.max_count})"
                        )

        if missing_assessments:

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates yet. "
                            "The following required assessments are missing: "
                            + ", ".join(
                                missing_assessments
                            )
                        ),
                },
            )

        # ====================================================
        # CHECK ATTENDANCE DATA WHEN ATTENDANCE HAS A WEIGHT
        # ====================================================
        attendance_rule = rules.filter(assessment_type=AcademicSchemeRule.AssessmentType.ATTENDANCE).first()
        if attendance_rule:
            from attendance.models import Attendance
            missing_attendance = []
            for term in required_terms:
                students_with_attendance = set(Attendance.objects.filter(
                    school=school, student__in=students, term=term
                ).values_list("student_id", flat=True))
                for student in students:
                    if student.id not in students_with_attendance:
                        missing_attendance.append(f"{student} - {term.name}")
            if missing_attendance:
                return render(request, "certificates/certificate_generation.html", {
                    "classrooms": classrooms, "templates": templates,
                    "error": "لا يمكن إصدار الشهادات لأن بيانات الحضور غير مسجلة لبعض الطلاب: " + ", ".join(missing_attendance),
                })

        # ====================================================
        # CHECK STUDENT GRADES
        # ====================================================

        missing_grades = []

        for classroom_subject in required_subjects:
            subject = classroom_subject.subject
            for term in required_terms:
                for rule in rules:
                    if rule.assessment_type == AcademicSchemeRule.AssessmentType.ATTENDANCE:
                        continue
                    assessments = Assessment.objects.filter(
                        school=school, classroom=classroom, subject=subject, term=term,
                        assessment_type=rule.assessment_type,
                    ).order_by("date", "id")[:rule.max_count]
                    for assessment in assessments:
                        graded_student_ids = set(Grade.objects.filter(
                            school=school, assessment=assessment, student__in=students
                        ).values_list("student_id", flat=True))
                        for student in students:
                            if student.id not in graded_student_ids:
                                missing_grades.append(
                                    f"{student} - {subject.name} - {term.name} - {assessment.title}"
                                )

        if missing_grades:

            return render(
                request,
                "certificates/certificate_generation.html",
                {
                    "classrooms":
                        classrooms,

                    "templates":
                        templates,

                    "error":
                        (
                            "Cannot generate certificates yet. "
                            "Some students are missing grades: "
                            + ", ".join(
                                missing_grades
                            )
                        ),
                },
            )

        # ====================================================
        # ALL ASSESSMENTS FOR CERTIFICATE CALCULATION
        # ====================================================

        assessments = (
            Assessment.objects
            .filter(
                school=school,
                classroom=classroom,
                term__in=required_terms,
            )
            .order_by(
                "date",
                "id",
            )
        )

        # ====================================================
        # GENERATE CLASS PDF
        # ====================================================

        pdf_buffer = (
            generate_classroom_certificates_pdf(
                template=template,
                students=students,
                classroom=classroom,
                assessments=assessments,
                school=school,
            )
        )

        return FileResponse(
            pdf_buffer,
            as_attachment=True,
            filename=(
                f"certificates_{classroom.name}.pdf"
            ),
            content_type="application/pdf",
        )

    return render(
        request,
        "certificates/certificate_generation.html",
        {
            "classrooms":
                classrooms,

            "templates":
                templates,
        },
    )