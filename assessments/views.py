from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import Classroom, TeachingAssignment
from students.models import StudentProfile

from .forms import AssessmentForm
from .models import Assessment, Grade
from schools.decorators import teacher_required


@login_required
@teacher_required
def assessment_list(request):
    teacher = request.user
    school = teacher.school

    assessments = (
        Assessment.objects
        .filter(
            school=school,
            classroom__teaching_assignments__teacher=teacher,
            subject__teaching_assignments__teacher=teacher,
        )
        .select_related(
            "classroom",
            "subject",
            "term",
            "term__academic_year",
        )
        .distinct()
        .order_by("-date", "-id")
    )

    return render(
        request,
        "schools/teacher/assessments/list.html",
        {
            "assessments": assessments,
        },
    )


@login_required
@teacher_required
def assessment_create(request):
    teacher = request.user
    school = teacher.school

    if request.method == "POST":
        form = AssessmentForm(
            request.POST,
            teacher=teacher,
            school=school,
        )

        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.school = school
            assessment.created_by = teacher
            assessment.save()

            messages.success(
                request,
                "تم إنشاء التقييم بنجاح.",
            )

            return redirect(
                "teacher:assessment_detail",
                pk=assessment.pk,
            )
    else:
        form = AssessmentForm(
            teacher=teacher,
            school=school,
        )

    return render(
        request,
        "schools/teacher/assessments/form.html",
        {
            "form": form,
            "title": "إنشاء تقييم جديد",
        },
    )


@login_required
@teacher_required
def assessment_edit(request, pk):
    teacher = request.user
    school = teacher.school

    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "classroom",
            "subject",
            "term",
        ),
        pk=pk,
        school=school,
    )

    # Only the teacher who created the assessment
    # can edit it.
    if assessment.created_by_id != teacher.id:
        messages.error(
            request,
            "لا يمكنك تعديل هذا التقييم.",
        )
        return redirect("teacher:assessment_list")

    if request.method == "POST":
        form = AssessmentForm(
            request.POST,
            instance=assessment,
            teacher=teacher,
            school=school,
        )

        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.school = school
            assessment.save()

            messages.success(
                request,
                "تم تعديل التقييم بنجاح.",
            )

            return redirect(
                "teacher:assessment_detail",
                pk=assessment.pk,
            )
    else:
        form = AssessmentForm(
            instance=assessment,
            teacher=teacher,
            school=school,
        )

    return render(
        request,
        "schools/teacher/assessments/form.html",
        {
            "form": form,
            "title": "تعديل التقييم",
            "assessment": assessment,
        },
    )


@login_required
@teacher_required
def assessment_delete(request, pk):
    teacher = request.user
    school = teacher.school

    assessment = get_object_or_404(
        Assessment,
        pk=pk,
        school=school,
    )

    if assessment.created_by_id != teacher.id:
        messages.error(
            request,
            "لا يمكنك حذف هذا التقييم.",
        )
        return redirect("teacher:assessment_list")

    if request.method == "POST":
        assessment.delete()

        messages.success(
            request,
            "تم حذف التقييم بنجاح.",
        )

        return redirect("teacher:assessment_list")

    return render(
        request,
        "schools/teacher/assessments/delete.html",
        {
            "assessment": assessment,
        },
    )


@login_required
@teacher_required
def assessment_detail(request, pk):
    teacher = request.user
    school = teacher.school

    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "classroom",
            "subject",
            "term",
            "term__academic_year",
            "created_by",
        ),
        pk=pk,
        school=school,
    )

    # The teacher must actually teach this
    # classroom + subject combination.
    assignment_exists = TeachingAssignment.objects.filter(
        school=school,
        teacher=teacher,
        classroom=assessment.classroom,
        subject=assessment.subject,
    ).exists()

    if not assignment_exists:
        messages.error(
            request,
            "لا يمكنك الوصول إلى هذا التقييم.",
        )
        return redirect("teacher:assessment_list")

    students = (
        StudentProfile.objects
        .filter(
            school=school,
            classroom=assessment.classroom,
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__username")
    )

    grades = {
        grade.student_id: grade
        for grade in Grade.objects.filter(
            school=school,
            assessment=assessment,
        ).select_related("student")
    }

    student_rows = []

    for student in students:
        student_rows.append(
            {
                "student": student,
                "grade": grades.get(student.id),
            }
        )

    return render(
        request,
        "schools/teacher/assessments/detail.html",
        {
            "assessment": assessment,
            "student_rows": student_rows,
        },
    )


@login_required
@teacher_required
def assessment_grades(request, pk):
    teacher = request.user
    school = teacher.school

    assessment = get_object_or_404(
        Assessment.objects.select_related(
            "classroom",
            "subject",
            "term",
        ),
        pk=pk,
        school=school,
    )

    assignment_exists = TeachingAssignment.objects.filter(
        school=school,
        teacher=teacher,
        classroom=assessment.classroom,
        subject=assessment.subject,
    ).exists()

    if not assignment_exists:
        messages.error(
            request,
            "لا يمكنك تسجيل درجات هذا التقييم.",
        )
        return redirect("teacher:assessment_list")

    students = (
        StudentProfile.objects
        .filter(
            school=school,
            classroom=assessment.classroom,
        )
        .select_related("user")
        .order_by("user__first_name", "user__last_name", "user__username")
    )

    existing_grades = {
        grade.student_id: grade
        for grade in Grade.objects.filter(
            school=school,
            assessment=assessment,
        )
    }

    if request.method == "POST":
        errors = []

        with transaction.atomic():
            for student in students:
                field_name = f"score_{student.id}"
                raw_score = request.POST.get(field_name, "").strip()

                # Empty means no grade entered.
                if raw_score == "":
                    continue

                try:
                    score = float(raw_score)
                except (TypeError, ValueError):
                    errors.append(
                        f"درجة الطالب {student} غير صحيحة."
                    )
                    continue

                if score < 0:
                    errors.append(
                        f"درجة الطالب {student} لا يمكن أن تكون سالبة."
                    )
                    continue

                if score > float(assessment.max_score):
                    errors.append(
                        f"درجة الطالب {student} لا يمكن أن تتجاوز "
                        f"{assessment.max_score}."
                    )
                    continue

                grade = existing_grades.get(student.id)

                if grade:
                    grade.score = score
                    grade.recorded_by = teacher
                    grade.save()
                else:
                    Grade.objects.create(
                        school=school,
                        assessment=assessment,
                        student=student,
                        score=score,
                        recorded_by=teacher,
                    )

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(
                request,
                "تم حفظ الدرجات بنجاح.",
            )

        return redirect(
            "teacher:assessment_grades",
            pk=assessment.pk,
        )

    student_rows = []

    for student in students:
        student_rows.append(
            {
                "student": student,
                "grade": existing_grades.get(student.id),
            }
        )

    return render(
        request,
        "schools/teacher/assessments/grades.html",
        {
            "assessment": assessment,
            "student_rows": student_rows,
        },
    )