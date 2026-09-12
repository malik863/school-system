from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, Count, Q, Sum
from datetime import date
from academics.models import (
    AcademicScheme,
    Classroom,
    ClassroomSubject,
    Subject,
    TeachingAssignment,
)
from students.models import StudentProfile

from students.models import StudentProfile
from attendance.models import Attendance
from assessments.models import Assessment, Grade

from .decorators import (
    school_admin_required,
    teacher_required,
)
from .forms import (
    AcademicYearForm,
    ClassroomForm,
    StudentCreateForm,
    StudentUpdateForm,
    SubjectForm,
    TeacherCreateForm,
    TeacherUpdateForm,
    TermForm,
)
from .models import AcademicYear, Term


User = get_user_model()


def get_form_kwargs(request, **extra):
    kwargs = {"school": request.user.school}
    kwargs.update(extra)
    return kwargs


# ============================================================
# DASHBOARD
# ============================================================

@school_admin_required
def manager_dashboard(request):
    school = request.user.school

    context = {
        "total_teachers": User.objects.filter(
            school=school,
            role=User.Role.TEACHER,
        ).count(),
        "total_students": StudentProfile.objects.filter(
            school=school,
        ).count(),
        "total_classes": Classroom.objects.filter(
            school=school,
        ).count(),
        "total_subjects": Subject.objects.filter(
            school=school,
        ).count(),
        "current_year": AcademicYear.objects.filter(
            school=school,
            is_current=True,
        ).first(),
        "current_term": Term.objects.filter(
            school=school,
            is_current=True,
        ).first(),
    }
    return render(request, "schools/dashboard.html", context)


# ============================================================
# TEACHERS
# ============================================================

@school_admin_required
def teacher_list(request):
    teachers = User.objects.filter(
        school=request.user.school,
        role=User.Role.TEACHER,
    ).order_by("first_name", "last_name", "username")
    return render(request, "schools/teachers/teacher_list.html", {"teachers": teachers})


@school_admin_required
def teacher_create(request):
    if request.method == "POST":
        form = TeacherCreateForm(request.POST, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم إضافة المعلم بنجاح.")
            return redirect("manager:teacher_list")
    else:
        form = TeacherCreateForm(**get_form_kwargs(request))

    return render(
        request,
        "schools/teachers/teacher_form.html",
        {"form": form, "title": "إضافة معلم جديد"},
    )


@school_admin_required
def teacher_edit(request, pk):
    teacher = get_object_or_404(
        User,
        pk=pk,
        school=request.user.school,
        role=User.Role.TEACHER,
    )

    if request.method == "POST":
        form = TeacherUpdateForm(request.POST, instance=teacher)
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل بيانات المعلم بنجاح.")
            return redirect("manager:teacher_list")
    else:
        form = TeacherUpdateForm(instance=teacher)

    return render(
        request,
        "schools/teachers/teacher_form.html",
        {"form": form, "title": "تعديل بيانات المعلم", "teacher": teacher},
    )


@school_admin_required
def teacher_toggle_active(request, pk):
    teacher = get_object_or_404(
        User,
        pk=pk,
        school=request.user.school,
        role=User.Role.TEACHER,
    )

    if request.method != "POST":
        return redirect("manager:teacher_list")

    teacher.is_active = not teacher.is_active
    teacher.save(update_fields=["is_active"])

    messages.success(
        request,
        "تم تفعيل المعلم بنجاح." if teacher.is_active else "تم تعطيل المعلم بنجاح.",
    )
    return redirect("manager:teacher_list")


@school_admin_required
def teacher_delete(request, pk):
    teacher = get_object_or_404(
        User,
        pk=pk,
        school=request.user.school,
        role=User.Role.TEACHER,
    )

    if request.method == "POST":
        teacher.delete()
        messages.success(request, "تم حذف المعلم بنجاح.")
        return redirect("manager:teacher_list")

    return render(
        request,
        "schools/teachers/teacher_confirm_delete.html",
        {"teacher": teacher},
    )


# ============================================================
# CLASSROOMS
# ============================================================

@school_admin_required
def class_list(request):
    school = request.user.school
    query = request.GET.get("q", "").strip()
    academic_year_id = request.GET.get("academic_year", "").strip()

    classes = Classroom.objects.filter(
        school=school,
    ).select_related("academic_year", "lead_teacher")

    if query:
        search_filter = (
            Q(name__icontains=query)
            | Q(lead_teacher__first_name__icontains=query)
            | Q(lead_teacher__last_name__icontains=query)
            | Q(lead_teacher__username__icontains=query)
        )
        if query.isdigit():
            search_filter |= Q(grade_level=int(query))
        classes = classes.filter(search_filter)

    if academic_year_id:
        classes = classes.filter(academic_year_id=academic_year_id)

    classes = classes.order_by(
        "academic_year__start_date",
        "grade_level",
        "name",
    )

    academic_years = AcademicYear.objects.filter(
        school=school,
    ).order_by("-start_date")

    paginator = Paginator(classes, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "schools/classes/class_list.html",
        {
            "classes": page_obj,
            "page_obj": page_obj,
            "academic_years": academic_years,
            "query": query,
            "selected_academic_year": academic_year_id,
        },
    )


@school_admin_required
def class_create(request):
    if request.method == "POST":
        form = ClassroomForm(
            request.POST,
            **get_form_kwargs(request)
        )

        if form.is_valid():
            classroom = form.save(commit=False)
            classroom.school = request.user.school
            classroom.save()

            messages.success(
                request,
                "تم إنشاء الفصل بنجاح."
            )

            return redirect("manager:class_list")

    else:
        form = ClassroomForm(
            **get_form_kwargs(request)
        )

    return render(
        request,
        "schools/classes/class_form.html",
        {
            "form": form,
            "title": "إضافة فصل جديد",
        },
    )


@school_admin_required
def class_edit(request, pk):
    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = ClassroomForm(request.POST, instance=classroom, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل الفصل بنجاح.")
            return redirect("manager:class_list")
    else:
        form = ClassroomForm(instance=classroom, **get_form_kwargs(request))

    return render(
        request,
        "schools/classes/class_form.html",
        {"form": form, "title": "تعديل الفصل", "classroom": classroom},
    )


@school_admin_required
def class_delete(request, pk):
    classroom = get_object_or_404(
        Classroom,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        classroom.delete()
        messages.success(request, "تم حذف الفصل بنجاح.")
        return redirect("manager:class_list")

    return render(
        request,
        "schools/classes/class_confirm_delete.html",
        {"classroom": classroom},
    )


# ============================================================
# SUBJECTS
# ============================================================

@school_admin_required
def subject_list(request):
    subjects = Subject.objects.filter(
        school=request.user.school,
    ).order_by("name")
    return render(request, "schools/subjects/subject_list.html", {"subjects": subjects})


@school_admin_required
def subject_create(request):
    if request.method == "POST":
        form = SubjectForm(request.POST, **get_form_kwargs(request))
        if form.is_valid():
            subject = form.save(commit=False)
            subject.school = request.user.school
            subject.save()
            messages.success(request, "تم إضافة المادة بنجاح.")
            return redirect("manager:subject_list")
    else:
        form = SubjectForm(**get_form_kwargs(request))

    return render(
        request,
        "schools/subjects/subject_form.html",
        {"form": form, "title": "إضافة مادة جديدة"},
    )


@school_admin_required
def subject_edit(request, pk):
    subject = get_object_or_404(
        Subject,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = SubjectForm(request.POST, instance=subject, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل المادة بنجاح.")
            return redirect("manager:subject_list")
    else:
        form = SubjectForm(instance=subject, **get_form_kwargs(request))

    return render(
        request,
        "schools/subjects/subject_form.html",
        {"form": form, "title": "تعديل المادة", "subject": subject},
    )


@school_admin_required
def subject_delete(request, pk):
    subject = get_object_or_404(
        Subject,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        subject.delete()
        messages.success(request, "تم حذف المادة بنجاح.")
        return redirect("manager:subject_list")

    return render(
        request,
        "schools/subjects/subject_confirm_delete.html",
        {"subject": subject},
    )


# ============================================================
# STUDENTS
# ============================================================

@school_admin_required
def student_list(request):
    school = request.user.school
    query = request.GET.get("q", "").strip()
    classroom_id = request.GET.get("classroom", "").strip()

    students = StudentProfile.objects.filter(
        school=school,
    ).select_related("user", "classroom")

    if query:
        students = students.filter(
            Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__username__icontains=query)
            | Q(student_number__icontains=query)
            | Q(parent_phone__icontains=query)
        )

    if classroom_id:
        students = students.filter(classroom_id=classroom_id)

    students = students.order_by(
        "user__first_name",
        "user__last_name",
        "user__username",
    )

    classrooms = Classroom.objects.filter(
        school=school,
    ).select_related("academic_year").order_by(
        "academic_year__start_date",
        "grade_level",
        "name",
    )

    paginator = Paginator(students, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "schools/students/student_list.html",
        {
            "students": page_obj,
            "page_obj": page_obj,
            "classrooms": classrooms,
            "query": query,
            "selected_classroom": classroom_id,
        },
    )


@school_admin_required
def student_create(request):
    if request.method == "POST":
        form = StudentCreateForm(request.POST, **get_form_kwargs(request))
        if form.is_valid():
            with transaction.atomic():
                form.save()
            messages.success(request, "تم تسجيل الطالب بنجاح.")
            return redirect("manager:student_list")
    else:
        form = StudentCreateForm(**get_form_kwargs(request))

    return render(
        request,
        "schools/students/student_form.html",
        {"form": form, "title": "تسجيل طالب جديد"},
    )


@school_admin_required
def student_edit(request, pk):
    student = get_object_or_404(
        StudentProfile.objects.select_related("user"),
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = StudentUpdateForm(request.POST, instance=student, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل بيانات الطالب بنجاح.")
            return redirect("manager:student_list")
    else:
        form = StudentUpdateForm(instance=student, **get_form_kwargs(request))

    return render(
        request,
        "schools/students/student_form.html",
        {"form": form, "title": "تعديل بيانات الطالب", "student": student},
    )


@school_admin_required
def student_toggle_active(request, pk):
    student = get_object_or_404(
        StudentProfile,
        pk=pk,
        school=request.user.school,
    )

    if request.method != "POST":
        return redirect("manager:student_list")

    student.is_active = not student.is_active
    student.save(update_fields=["is_active"])

    student.user.is_active = student.is_active
    student.user.save(update_fields=["is_active"])

    messages.success(
        request,
        "تم تفعيل الطالب بنجاح." if student.is_active else "تم تعطيل الطالب بنجاح.",
    )
    return redirect("manager:student_list")


@school_admin_required
def student_delete(request, pk):
    student = get_object_or_404(
        StudentProfile.objects.select_related("user"),
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        user = student.user
        with transaction.atomic():
            student.delete()
            user.delete()
        messages.success(request, "تم حذف الطالب بنجاح.")
        return redirect("manager:student_list")

    return render(
        request,
        "schools/students/student_confirm_delete.html",
        {"student": student},
    )


# ============================================================
# ACADEMIC YEARS
# ============================================================

@school_admin_required
def academic_year_list(request):
    school = request.user.school
    years = AcademicYear.objects.filter(school=school)
    terms = Term.objects.filter(school=school).select_related("academic_year")
    return render(
        request,
        "schools/academic/year_term_list.html",
        {"years": years, "terms": terms},
    )


@school_admin_required
def academic_year_create(request):
    if request.method == "POST":
        form = AcademicYearForm(request.POST, **get_form_kwargs(request))
        if form.is_valid():
            year = form.save(commit=False)
            year.school = request.user.school
            year.save()
            messages.success(request, "تم إضافة العام الدراسي بنجاح.")
            return redirect("manager:academic_year_list")
    else:
        form = AcademicYearForm(**get_form_kwargs(request))

    return render(
        request,
        "schools/academic/year_form.html",
        {"form": form, "title": "إضافة عام دراسي جديد"},
    )


@school_admin_required
def academic_year_edit(request, pk):
    year = get_object_or_404(
        AcademicYear,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = AcademicYearForm(request.POST, instance=year, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل العام الدراسي بنجاح.")
            return redirect("manager:academic_year_list")
    else:
        form = AcademicYearForm(instance=year, **get_form_kwargs(request))

    return render(
        request,
        "schools/academic/year_form.html",
        {"form": form, "title": "تعديل العام الدراسي", "year": year},
    )


@school_admin_required
def academic_year_delete(request, pk):
    year = get_object_or_404(
        AcademicYear,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        year.delete()
        messages.success(request, "تم حذف العام الدراسي بنجاح.")
        return redirect("manager:academic_year_list")

    return render(
        request,
        "schools/academic/year_confirm_delete.html",
        {"year": year},
    )


# ============================================================
# TERMS
# ============================================================

@school_admin_required
def term_create(request):
    if request.method == "POST":
        form = TermForm(request.POST, **get_form_kwargs(request))
        if form.is_valid():
            term = form.save(commit=False)
            term.school = request.user.school
            term.save()
            messages.success(request, "تم إضافة الترم بنجاح.")
            return redirect("manager:academic_year_list")
    else:
        form = TermForm(**get_form_kwargs(request))

    return render(
        request,
        "schools/academic/term_form.html",
        {"form": form, "title": "إضافة ترم جديد"},
    )


@school_admin_required
def term_edit(request, pk):
    term = get_object_or_404(
        Term,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        form = TermForm(request.POST, instance=term, **get_form_kwargs(request))
        if form.is_valid():
            form.save()
            messages.success(request, "تم تعديل الترم بنجاح.")
            return redirect("manager:academic_year_list")
    else:
        form = TermForm(instance=term, **get_form_kwargs(request))

    return render(
        request,
        "schools/academic/term_form.html",
        {"form": form, "title": "تعديل الترم", "term": term},
    )


@school_admin_required
def term_delete(request, pk):
    term = get_object_or_404(
        Term,
        pk=pk,
        school=request.user.school,
    )

    if request.method == "POST":
        term.delete()
        messages.success(request, "تم حذف الترم بنجاح.")
        return redirect("manager:academic_year_list")

    return render(
        request,
        "schools/academic/term_confirm_delete.html",
        {"term": term},
    )




# ============================================================
# TEACHER DASHBOARD
# ============================================================

@teacher_required
def teacher_dashboard(request):
    teacher = request.user
    school = teacher.school

    assignments = (
        TeachingAssignment.objects
        .filter(
            school=school,
            teacher=teacher,
        )
        .select_related(
            "classroom",
            "subject",
            "classroom__academic_year",
        )
        .order_by(
            "classroom__grade_level",
            "classroom__name",
            "subject__name",
        )
    )

    total_assignments = assignments.count()

    total_classes = (
        assignments
        .values("classroom_id")
        .distinct()
        .count()
    )

    total_subjects = (
        assignments
        .values("subject_id")
        .distinct()
        .count()
    )

    lead_classes = (
        Classroom.objects
        .filter(
            school=school,
            lead_teacher=teacher,
        )
        .select_related("academic_year")
        .order_by(
            "grade_level",
            "name",
        )
    )

    context = {
        "assignments": assignments,
        "total_assignments": total_assignments,
        "total_classes": total_classes,
        "total_subjects": total_subjects,
        "lead_classes": lead_classes,
        "total_lead_classes": lead_classes.count(),
    }

    return render(
        request,
        "schools/teacher/dashboard.html",
        context,
    )


@teacher_required
def teacher_assignments(request):
    teacher = request.user
    school = teacher.school

    assignments = (
        TeachingAssignment.objects
        .filter(
            school=school,
            teacher=teacher,
        )
        .select_related(
            "classroom",
            "subject",
            "classroom__academic_year",
        )
        .order_by(
            "classroom__grade_level",
            "classroom__name",
            "subject__name",
        )
    )

    return render(
        request,
        "schools/teacher/assignments.html",
        {
            "assignments": assignments,
        },
    )



@teacher_required
def teacher_classes(request):
    teacher = request.user
    school = teacher.school

    classes = (
        Classroom.objects
        .filter(
            school=school,
            lead_teacher=teacher,
        )
        .select_related("academic_year")
        .prefetch_related("students")
        .order_by("grade_level", "name")
    )

    return render(
        request,
        "schools/teacher/classes.html",
        {
            "classes": classes,
        },
    )


@teacher_required
def teacher_class_detail(request, pk):
    teacher = request.user
    school = teacher.school

    classroom = get_object_or_404(
        Classroom.objects
        .select_related(
            "academic_year",
            "lead_teacher",
        ),
        pk=pk,
        school=school,
        lead_teacher=teacher,
    )

    students = list(
        StudentProfile.objects
        .filter(
            school=school,
            classroom=classroom,
            is_active=True,
        )
        .select_related("user")
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    # ---------------------------------------------------------
    # Attendance
    # ---------------------------------------------------------

    attendance_records = Attendance.objects.filter(
        school=school,
        classroom=classroom,
        student__in=students,
    )

    attendance_stats = (
        attendance_records
        .values("student_id")
        .annotate(
            total_days=Count("id"),
            attended_days=Count(
                "id",
                filter=Q(
                    status__in=[
                        Attendance.Status.PRESENT,
                        Attendance.Status.LATE,
                        Attendance.Status.EXCUSED,
                    ]
                ),
            ),
        )
    )

    attendance_by_student = {
        item["student_id"]: item
        for item in attendance_stats
    }

    # ---------------------------------------------------------
    # Grades / Current Performance
    # ---------------------------------------------------------

    grade_stats = (
        Grade.objects
        .filter(
            school=school,
            student__in=students,
            assessment__classroom=classroom,
        )
        .values("student_id")
        .annotate(
            total_score=Sum("score"),
            total_max_score=Sum("assessment__max_score"),
        )
    )

    assessment_count = Assessment.objects.filter(
    school=school,
    classroom=classroom,
    ).count()

    grades_by_student = {
        item["student_id"]: item
        for item in grade_stats
    }

    # ---------------------------------------------------------
    # Attach calculated data to each student
    # ---------------------------------------------------------

    for student in students:

        # Attendance
        attendance = attendance_by_student.get(
            student.pk,
            {
                "total_days": 0,
                "attended_days": 0,
            },
        )

        total_days = attendance["total_days"]
        attended_days = attendance["attended_days"]

        if total_days:
            student.attendance_percentage = round(
                (attended_days / total_days) * 100,
                1,
            )
        else:
            student.attendance_percentage = None

        # Current performance
        grades = grades_by_student.get(student.pk)

        if grades and grades["total_max_score"]:
            student.performance_percentage = round(
                (
                    float(grades["total_score"])
                    / float(grades["total_max_score"])
                ) * 100,
                1,
            )
        else:
            student.performance_percentage = None

    # ---------------------------------------------------------
    # Class statistics
    # ---------------------------------------------------------

    student_count = len(students)

    students_with_attendance = [
        student
        for student in students
        if student.attendance_percentage is not None
    ]

    if students_with_attendance:
        class_attendance = round(
            sum(
                student.attendance_percentage
                for student in students_with_attendance
            )
            / len(students_with_attendance),
            1,
        )
    else:
        class_attendance = None

    students_with_performance = [
        student
        for student in students
        if student.performance_percentage is not None
    ]

    if students_with_performance:
        class_average = round(
            sum(
                student.performance_percentage
                for student in students_with_performance
            )
            / len(students_with_performance),
            1,
        )
    else:
        class_average = None

    return render(
        request,
        "schools/teacher/class_detail.html",
        {
            "classroom": classroom,
            "students": students,

            "student_count": student_count,
            "class_attendance": class_attendance,
            "class_average": class_average,
            "assessment_count": assessment_count,
        },
    )

@teacher_required
def teacher_subjects(request):
    teacher = request.user
    school = teacher.school

    assignments = (
        TeachingAssignment.objects
        .filter(
            school=school,
            teacher=teacher,
        )
        .select_related(
            "classroom",
            "classroom__academic_year",
            "subject",
        )
        .order_by(
            "classroom__grade_level",
            "classroom__name",
            "subject__name",
        )
    )

    return render(
        request,
        "schools/teacher/subjects.html",
        {
            "assignments": assignments,
        },
    )


@teacher_required
def teacher_subject_detail(request, pk):
    teacher = request.user
    school = teacher.school

    assignment = get_object_or_404(
        TeachingAssignment.objects
        .select_related(
            "classroom",
            "classroom__academic_year",
            "subject",
        ),
        pk=pk,
        school=school,
        teacher=teacher,
    )

    classroom = assignment.classroom
    subject = assignment.subject

    students = list(
        StudentProfile.objects
        .filter(
            school=school,
            classroom=classroom,
            is_active=True,
        )
        .select_related("user")
        .order_by(
            "user__first_name",
            "user__last_name",
        )
    )

    # ---------------------------------------------------------
    # Attendance
    # ---------------------------------------------------------

    attendance_records = Attendance.objects.filter(
        school=school,
        classroom=classroom,
        student__in=students,
    )

    attendance_stats = (
        attendance_records
        .values("student_id")
        .annotate(
            total_days=Count("id"),
            attended_days=Count(
                "id",
                filter=Q(
                    status__in=[
                        Attendance.Status.PRESENT,
                        Attendance.Status.LATE,
                        Attendance.Status.EXCUSED,
                    ]
                ),
            ),
        )
    )

    attendance_by_student = {
        item["student_id"]: item
        for item in attendance_stats
    }

    # ---------------------------------------------------------
    # Grades for THIS subject only
    # ---------------------------------------------------------

    grades = (
        Grade.objects
        .filter(
            school=school,
            student__in=students,
            assessment__classroom=classroom,
            assessment__subject=subject,
        )
        .select_related(
            "assessment",
            "assessment__term",
        )
        .order_by(
            "student_id",
            "-assessment__date",
            "-assessment__id",
        )
    )

    grade_stats = (
        grades
        .values("student_id")
        .annotate(
            total_score=Sum("score"),
            total_max_score=Sum("assessment__max_score"),
        )
    )

    grades_by_student = {
        item["student_id"]: item
        for item in grade_stats
    }

    # ---------------------------------------------------------
    # Attach statistics to students
    # ---------------------------------------------------------

    for student in students:

        # Attendance
        attendance = attendance_by_student.get(
            student.pk,
            {
                "total_days": 0,
                "attended_days": 0,
            },
        )

        total_days = attendance["total_days"]
        attended_days = attendance["attended_days"]

        if total_days:
            student.attendance_percentage = round(
                (attended_days / total_days) * 100,
                1,
            )
        else:
            student.attendance_percentage = None

        # Subject performance
        grade_data = grades_by_student.get(student.pk)

        if grade_data and grade_data["total_max_score"]:
            student.performance_percentage = round(
                (
                    float(grade_data["total_score"])
                    / float(grade_data["total_max_score"])
                ) * 100,
                1,
            )
        else:
            student.performance_percentage = None

    # ---------------------------------------------------------
    # Subject statistics
    # ---------------------------------------------------------

    student_count = len(students)

    students_with_attendance = [
        student
        for student in students
        if student.attendance_percentage is not None
    ]

    if students_with_attendance:
        subject_attendance = round(
            sum(
                student.attendance_percentage
                for student in students_with_attendance
            )
            / len(students_with_attendance),
            1,
        )
    else:
        subject_attendance = None

    students_with_performance = [
        student
        for student in students
        if student.performance_percentage is not None
    ]

    if students_with_performance:
        subject_average = round(
            sum(
                student.performance_percentage
                for student in students_with_performance
            )
            / len(students_with_performance),
            1,
        )
    else:
        subject_average = None

    # ---------------------------------------------------------
    # Number of assessments
    # ---------------------------------------------------------

    assessment_count = Assessment.objects.filter(
        school=school,
        classroom=classroom,
        subject=subject,
    ).count()

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------

    return render(
        request,
        "schools/teacher/subject_detail.html",
        {
            "assignment": assignment,
            "classroom": classroom,
            "subject": subject,
            "students": students,

            "student_count": student_count,
            "subject_attendance": subject_attendance,
            "subject_average": subject_average,
            "assessment_count": assessment_count,
        },
    )


@teacher_required
def teacher_student_detail(request, student_id):
    teacher = request.user
    school = teacher.school

    student = get_object_or_404(
        StudentProfile.objects
        .select_related("user", "classroom", "classroom__academic_year"),
        pk=student_id,
        school=school,
        classroom__lead_teacher=teacher,
    )

    classroom = student.classroom

    # -------------------------
    # Attendance
    # -------------------------
    attendance_records = Attendance.objects.filter(
        school=school,
        student=student,
        classroom=classroom,
    )

    total_attendance = attendance_records.count()

    attended_attendance = attendance_records.filter(
        status__in=[
            Attendance.Status.PRESENT,
            Attendance.Status.LATE,
            Attendance.Status.EXCUSED,
        ]
    ).count()

    attendance_percentage = None

    if total_attendance:
        attendance_percentage = round(
            (attended_attendance / total_attendance) * 100,
            1,
        )

    # -------------------------
    # Grades
    # -------------------------
    grades = (
        Grade.objects
        .filter(
            school=school,
            student=student,
            assessment__classroom=classroom,
        )
        .select_related(
            "assessment",
            "assessment__subject",
            "assessment__term",
        )
        .order_by(
            "assessment__subject__name",
            "-assessment__date",
            "-assessment__id",
        )
    )

    # -------------------------
    # Overall performance
    # -------------------------
    total_score = grades.aggregate(
        total=Sum("score")
    )["total"]

    total_max_score = grades.aggregate(
        total=Sum("assessment__max_score")
    )["total"]

    performance_percentage = None

    if total_max_score:
        performance_percentage = round(
            (float(total_score) / float(total_max_score)) * 100,
            1,
        )

    # -------------------------
    # Group grades by subject
    # -------------------------
    subjects = {}

    for grade in grades:
        subject = grade.assessment.subject

        if subject.id not in subjects:
            subjects[subject.id] = {
                "subject": subject,
                "grades": [],
                "total_score": 0,
                "total_max_score": 0,
            }

        subjects[subject.id]["grades"].append(grade)

        subjects[subject.id]["total_score"] += float(grade.score)
        subjects[subject.id]["total_max_score"] += float(
            grade.assessment.max_score
        )

    # Calculate subject percentages
    for data in subjects.values():
        if data["total_max_score"]:
            data["percentage"] = round(
                (
                    data["total_score"]
                    / data["total_max_score"]
                ) * 100,
                1,
            )
        else:
            data["percentage"] = None

    # -------------------------
    # Age
    # -------------------------
    age = None

    if student.date_of_birth:
        today = date.today()

        age = (
            today.year
            - student.date_of_birth.year
            - (
                (today.month, today.day)
                < (
                    student.date_of_birth.month,
                    student.date_of_birth.day,
                )
            )
        )

    context = {
        "student": student,
        "classroom": classroom,
        "age": age,

        "attendance_percentage": attendance_percentage,
        "total_attendance": total_attendance,
        "attended_attendance": attended_attendance,

        "performance_percentage": performance_percentage,

        "subjects": subjects.values(),
    }

    return render(
        request,
        "schools/teacher/student_detail.html",
        context,
    )