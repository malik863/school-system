from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from schools.decorators import school_admin_required

from .forms import (
    ClassroomSubjectForm,
    GradeSchemeForm,
    TeachingAssignmentForm,
    AcademicSchemeForm,
    AcademicSchemeRuleForm,
)
from .models import (
    AcademicScheme,
    AcademicSchemeRule,
    Classroom,
    ClassroomSubject,
    GradeScheme,
    TeachingAssignment,
    Subject,
)


# =========================================================
# CLASSROOM SUBJECTS
# =========================================================

@school_admin_required
def classroom_subject_list(request):
    school = request.user.school

    classroom_subjects = (
        ClassroomSubject.objects
        .filter(school=school)
        .select_related(
            "classroom",
            "subject",
            "classroom__academic_year",
        )
        .order_by(
            "classroom__academic_year__name",
            "classroom__grade_level",
            "classroom__name",
            "subject__name",
        )
    )

    classrooms = (
        Classroom.objects
        .filter(school=school)
        .select_related("academic_year")
        .order_by(
            "academic_year__name",
            "grade_level",
            "name",
        )
    )

    return render(
        request,
        "schools/classroom_subjects/classroom_subject_list.html",
        {
            "classroom_subjects": classroom_subjects,
            "classrooms": classrooms,
        },
    )


@school_admin_required
def classroom_subject_create(request):
    school = request.user.school

    if request.method == "POST":
        form = ClassroomSubjectForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            classroom_subject = form.save(
                commit=False
            )

            classroom_subject.school = school
            classroom_subject.save()

            messages.success(
                request,
                "تمت إضافة المادة إلى الفصل بنجاح.",
            )

            return redirect(
                "manager:classroom_subject_list"
            )
    else:
        form = ClassroomSubjectForm(
            school=school
        )

    return render(
        request,
        "schools/classroom_subjects/classroom_subject_form.html",
        {
            "form": form,
            "title": "إضافة مادة إلى فصل",
        },
    )


@school_admin_required
def classroom_subject_delete(request, pk):
    classroom_subject = get_object_or_404(
        ClassroomSubject,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        classroom_subject.delete()

        messages.success(
            request,
            "تم حذف المادة من الفصل بنجاح.",
        )

        return redirect(
            "manager:classroom_subject_list"
        )

    return render(
        request,
        "schools/classroom_subjects/classroom_subject_confirm_delete.html",
        {
            "classroom_subject": classroom_subject,
        },
    )


# =========================================================
# TEACHING ASSIGNMENTS
# =========================================================

@school_admin_required
def teaching_assignment_list(request):
    school = request.user.school
    query = request.GET.get("q", "").strip()
    teacher_id = request.GET.get("teacher", "").strip()
    classroom_id = request.GET.get("classroom", "").strip()
    subject_id = request.GET.get("subject", "").strip()

    assignments = (
        TeachingAssignment.objects
        .filter(school=school)
        .select_related(
            "teacher",
            "classroom",
            "subject",
            "classroom__academic_year",
        )
    )

    if query:
        assignments = assignments.filter(
            Q(teacher__first_name__icontains=query)
            | Q(teacher__last_name__icontains=query)
            | Q(teacher__username__icontains=query)
            | Q(classroom__name__icontains=query)
            | Q(subject__name__icontains=query)
        )

    if teacher_id:
        assignments = assignments.filter(teacher_id=teacher_id)

    if classroom_id:
        assignments = assignments.filter(classroom_id=classroom_id)

    if subject_id:
        assignments = assignments.filter(subject_id=subject_id)

    assignments = assignments.order_by(
        "classroom__academic_year__name",
        "classroom__grade_level",
        "classroom__name",
        "subject__name",
    )

    User = get_user_model()
    teachers = User.objects.filter(
        school=school,
        role=User.Role.TEACHER,
    ).order_by("first_name", "last_name", "username")

    classrooms = Classroom.objects.filter(
        school=school,
    ).select_related("academic_year").order_by(
        "academic_year__start_date",
        "grade_level",
        "name",
    )

    subjects = Subject.objects.filter(
        school=school,
    ).order_by("name")

    paginator = Paginator(assignments, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "schools/assignments/teaching_assignments_list.html",
        {
            "assignments": page_obj,
            "page_obj": page_obj,
            "teachers": teachers,
            "classrooms": classrooms,
            "subjects": subjects,
            "query": query,
            "selected_teacher": teacher_id,
            "selected_classroom": classroom_id,
            "selected_subject": subject_id,
        },
    )


@school_admin_required
def teaching_assignment_create(request):
    school = request.user.school

    if request.method == "POST":
        form = TeachingAssignmentForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            assignment = form.save(
                commit=False
            )

            assignment.school = school
            assignment.save()

            messages.success(
                request,
                "تم إسناد المادة إلى المعلم بنجاح.",
            )

            return redirect(
                "manager:teaching_assignment_list"
            )
    else:
        form = TeachingAssignmentForm(
            school=school
        )

    return render(
        request,
        "schools/assignments/assignments_form.html",
        {
            "form": form,
            "title": "إضافة تكليف تدريسي",
        },
    )


@school_admin_required
def teaching_assignment_edit(request, pk):
    assignment = get_object_or_404(
        TeachingAssignment,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = TeachingAssignmentForm(
            request.POST,
            instance=assignment,
            school=request.user.school,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "تم تعديل التكليف التدريسي بنجاح.",
            )

            return redirect(
                "manager:teaching_assignment_list"
            )
    else:
        form = TeachingAssignmentForm(
            instance=assignment,
            school=request.user.school,
        )

    return render(
        request,
        "schools/assignments/assignments_form.html",
        {
            "form": form,
            "title": "تعديل التكليف التدريسي",
            "assignment": assignment,
        },
    )


@school_admin_required
def teaching_assignment_delete(request, pk):
    assignment = get_object_or_404(
        TeachingAssignment,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        assignment.delete()

        messages.success(
            request,
            "تم حذف التكليف التدريسي بنجاح.",
        )

        return redirect(
            "manager:teaching_assignment_list"
        )

    return render(
        request,
        "schools/assignments/assignment_confirm_delete.html",
        {
            "assignment": assignment,
        },
    )


# =========================================================
# GRADE SCHEMES
# =========================================================

@school_admin_required
def grade_scheme_list(request):
    school = request.user.school

    schemes = (
        GradeScheme.objects
        .filter(school=school)
        .select_related("subject")
        .prefetch_related(
            "classrooms",
            "classrooms__academic_year",
        )
        .order_by(
            "subject__name",
            "assessment_type",
        )
    )

    return render(
        request,
        "schools/grade_schemes/grade_scheme_list.html",
        {
            "schemes": schemes,
        },
    )


@school_admin_required
def grade_scheme_create(request):
    school = request.user.school

    if request.method == "POST":
        form = GradeSchemeForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            scheme = form.save(
                commit=False
            )

            scheme.school = school
            scheme.save()

            form.save_m2m()

            messages.success(
                request,
                "تم إنشاء نظام الدرجات بنجاح.",
            )

            return redirect(
                "manager:grade_scheme_list"
            )
    else:
        form = GradeSchemeForm(
            school=school
        )

    return render(
        request,
        "schools/grade_schemes/grade_scheme_form.html",
        {
            "form": form,
            "title": "إضافة نظام درجات",
        },
    )


@school_admin_required
def grade_scheme_edit(request, pk):
    scheme = get_object_or_404(
        GradeScheme,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = GradeSchemeForm(
            request.POST,
            instance=scheme,
            school=request.user.school,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "تم تعديل نظام الدرجات بنجاح.",
            )

            return redirect(
                "manager:grade_scheme_list"
            )
    else:
        form = GradeSchemeForm(
            instance=scheme,
            school=request.user.school,
        )

    return render(
        request,
        "schools/grade_schemes/grade_scheme_form.html",
        {
            "form": form,
            "title": "تعديل نظام الدرجات",
            "scheme": scheme,
        },
    )


@school_admin_required
def grade_scheme_delete(request, pk):
    scheme = get_object_or_404(
        GradeScheme,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        scheme.delete()

        messages.success(
            request,
            "تم حذف نظام الدرجات بنجاح.",
        )

        return redirect(
            "manager:grade_scheme_list"
        )

    return render(
        request,
        "schools/grade_schemes/grade_scheme_confirm_delete.html",
        {
            "scheme": scheme,
        },
    )



def sync_academic_scheme_subjects(scheme):
    """
    Synchronize ClassroomSubject records with the Academic Scheme.

    For every classroom in the scheme:
    - Add selected subjects.
    - Remove subjects that are no longer selected.
    """

    selected_subject_ids = set(
        scheme.subjects.values_list("id", flat=True)
    )

    for classroom in scheme.classrooms.all():

        # Remove subjects that are no longer part of the scheme.
        ClassroomSubject.objects.filter(
            school=scheme.school,
            classroom=classroom,
        ).exclude(
            subject_id__in=selected_subject_ids
        ).delete()

        # Add the subjects selected in the scheme.
        for subject_id in selected_subject_ids:
            ClassroomSubject.objects.get_or_create(
                school=scheme.school,
                classroom=classroom,
                subject_id=subject_id,
            )

# =========================================================
# ACADEMIC SCHEMES
# =========================================================

@school_admin_required
def academic_scheme_list(request):
    school = request.user.school

    schemes = (
        AcademicScheme.objects
        .filter(school=school)
        .prefetch_related(
            "classrooms",
            "subjects",
            "rules",
        )
        .order_by("name")
    )

    return render(
        request,
        "schools/academic_schemes/academic_scheme_list.html",
        {
            "schemes": schemes,
        },
    )

@school_admin_required
def academic_scheme_create(request):
    school = request.user.school

    if request.method == "POST":
        form = AcademicSchemeForm(
            request.POST,
            school=school,
        )

        if form.is_valid():
            scheme = form.save(
                commit=False
            )

            scheme.school = school
            scheme.save()

            form.save_m2m()
            sync_academic_scheme_subjects(scheme)

            messages.success(
                request,
                "تم إنشاء النظام الأكاديمي بنجاح.",
            )

            return redirect(
                "manager:academic_scheme_edit",
                pk=scheme.pk,
            )
    else:
        form = AcademicSchemeForm(
            school=school,
        )

    return render(
        request,
        "schools/academic_schemes/academic_scheme_form.html",
        {
            "form": form,
            "title": "إضافة نظام أكاديمي",
        },
    )


@school_admin_required
def academic_scheme_edit(request, pk):
    scheme = get_object_or_404(
        AcademicScheme,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = AcademicSchemeForm(
            request.POST,
            instance=scheme,
            school=request.user.school,
        )

        if form.is_valid():
            form.save()

            sync_academic_scheme_subjects(scheme)

            messages.success(
                request,
                "تم تعديل النظام الأكاديمي بنجاح.",
            )

            return redirect(
                "manager:academic_scheme_edit",
                pk=scheme.pk,
            )
    else:
        form = AcademicSchemeForm(
            instance=scheme,
            school=request.user.school,
        )

    rules = AcademicSchemeRule.objects.filter(
        school=request.user.school,
        scheme=scheme,
    ).order_by("assessment_type")

    total_weight = rules.aggregate(
        total=Sum("weight")
    )["total"] or 0

    return render(
        request,
        "schools/academic_schemes/academic_scheme_form.html",
        {
            "form": form,
            "title": "تعديل النظام الأكاديمي",
            "scheme": scheme,
            "rules": rules,
            "total_weight": total_weight,
        },
    )


@school_admin_required
def academic_scheme_delete(request, pk):
    scheme = get_object_or_404(
        AcademicScheme,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        scheme.delete()

        messages.success(
            request,
            "تم حذف النظام الأكاديمي بنجاح.",
        )

        return redirect(
            "manager:academic_scheme_list"
        )

    return render(
        request,
        "schools/academic_schemes/academic_scheme_confirm_delete.html",
        {
            "scheme": scheme,
        },
    )


@school_admin_required
def academic_scheme_rule_create(request, scheme_pk):
    school = request.user.school

    scheme = get_object_or_404(
        AcademicScheme,
        pk=scheme_pk,
        school=school,
    )

    if request.method == "POST":
        form = AcademicSchemeRuleForm(
            request.POST,
            school=school,
            scheme=scheme,
        )

        if form.is_valid():
            rule = form.save(
                commit=False
            )

            rule.school = school
            rule.scheme = scheme
            rule.save()

            messages.success(
                request,
                "تمت إضافة قاعدة الدرجات بنجاح.",
            )

            return redirect(
                "manager:academic_scheme_edit",
                pk=scheme.pk,
            )
    else:
        form = AcademicSchemeRuleForm(
            school=school,
            scheme=scheme,
        )

    return render(
        request,
        "schools/academic_schemes/rule_form.html",
        {
            "form": form,
            "scheme": scheme,
            "title": "إضافة قاعدة درجات",
        },
    )

@school_admin_required
def academic_scheme_rule_edit(request, pk):
    rule = get_object_or_404(
        AcademicSchemeRule,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = AcademicSchemeRuleForm(
            request.POST,
            instance=rule,
            school=request.user.school,
            scheme=rule.scheme,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "تم تعديل قاعدة الدرجات بنجاح.",
            )

            return redirect(
                "manager:academic_scheme_edit",
                pk=rule.scheme_id,
            )
    else:
        form = AcademicSchemeRuleForm(
            instance=rule,
            school=request.user.school,
            scheme=rule.scheme,
        )

    return render(
        request,
        "schools/academic_schemes/rule_form.html",
        {
            "form": form,
            "scheme": rule.scheme,
            "rule": rule,
            "title": "تعديل قاعدة درجات",
        },
    )


@school_admin_required
def academic_scheme_rule_delete(request, pk):
    rule = get_object_or_404(
        AcademicSchemeRule,
        pk=pk,
        school=request.user.school,
    )

    scheme_pk = rule.scheme_id

    if request.method == "POST":
        rule.delete()

        messages.success(
            request,
            "تم حذف قاعدة الدرجات بنجاح.",
        )

        return redirect(
            "manager:academic_scheme_edit",
            pk=scheme_pk,
        )

    return render(
        request,
        "schools/academic_schemes/rule_confirm_delete.html",
        {
            "rule": rule,
        },
    )