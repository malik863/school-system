from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Avg, Count, Q, Sum, F
from datetime import date, timedelta
from academics.grade_calculator import student_subject_breakdown, student_year_result, school_period_average
from academics.models import (
    AcademicScheme,
    Classroom,
    ClassroomSubject,
    Subject,
    TeachingAssignment,
)
from students.models import StudentProfile, StudentEnrollment

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


from django.shortcuts import render

def landing_page(request):
    return render(request, "schools/landing.html")


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
    today = date.today()

    # ============================================================
    # CURRENT ACADEMIC PERIOD
    # ============================================================

    current_year = (
        AcademicYear.objects
        .filter(
            school=school,
            is_current=True,
        )
        .first()
    )

    current_term = (
        Term.objects
        .filter(
            school=school,
            is_current=True,
        )
        .select_related("academic_year")
        .first()
    )

    # ============================================================
    # BASIC COUNTS
    # ============================================================

    total_teachers = User.objects.filter(
        school=school,
        role=User.Role.TEACHER,
        is_active=True,
    ).count()

    active_students = StudentProfile.objects.filter(
        school=school,
        is_active=True,
    )

    # If there is a current academic year, only students currently
    # assigned to classrooms from that academic year are counted.
    if current_year:
        active_students = active_students.filter(
            classroom__academic_year=current_year,
        )

    total_students = active_students.count()

    classrooms = Classroom.objects.filter(
        school=school,
    )

    if current_year:
        classrooms = classrooms.filter(
            academic_year=current_year,
        )

    classrooms = classrooms.order_by(
        "grade_level",
        "name",
    )

    total_classes = classrooms.count()

    # ============================================================
    # TODAY'S ATTENDANCE
    # ============================================================

    today_attendance = Attendance.objects.filter(
        school=school,
        date=today,
        student__is_active=True,
    )

    if current_term:
        today_attendance = today_attendance.filter(
            term=current_term,
        )

    # If there is a current year, make sure today's attendance
    # belongs to that academic year.
    if current_year:
        today_attendance = today_attendance.filter(
            term__academic_year=current_year,
        )

    today_recorded = today_attendance.count()

    today_present = today_attendance.filter(
        status__in=[
            Attendance.Status.PRESENT,
            Attendance.Status.LATE,
            Attendance.Status.EXCUSED,
        ]
    ).count()

    today_absent = today_attendance.filter(
        status=Attendance.Status.ABSENT,
    ).count()

    if today_recorded:
        attendance_today_percentage = round(
            (today_present / today_recorded) * 100,
            1,
        )
    else:
        attendance_today_percentage = None

    # How many active students have not had attendance recorded today?
    attendance_not_recorded = max(
        total_students - today_recorded,
        0,
    )

    # ============================================================
    # ACADEMIC PERFORMANCE - selectable term or whole academic year
    # ============================================================
    performance_terms = (Term.objects.filter(school=school, academic_year=current_year)
                         .order_by("start_date", "id") if current_year else Term.objects.none())
    requested_period = request.GET.get("performance_period", "")
    selected_performance_term = current_term
    performance_is_year = requested_period == "year"
    if requested_period.startswith("term:") and current_year:
        try:
            selected_performance_term = performance_terms.filter(pk=int(requested_period.split(":", 1)[1])).first() or current_term
        except (TypeError, ValueError):
            selected_performance_term = current_term
    academic_average = None
    if current_year:
        value = school_period_average(
            school, active_students.select_related("classroom"), current_year,
            term=None if performance_is_year else selected_performance_term,
        )
        if value is not None:
            academic_average = round(float(value), 1)

    # ============================================================
    # STUDENTS NEEDING ATTENTION
    # ============================================================

    # Easy to change later.
    LOW_ACADEMIC_THRESHOLD = 50
    LOW_ATTENDANCE_THRESHOLD = 75

    low_academic_student_ids = set()
    low_attendance_student_ids = set()

    # ------------------------------------------------------------
    # Low academic performance
    # ------------------------------------------------------------

    if current_term:

        student_grade_stats = (
            Grade.objects
            .filter(
                school=school,
                assessment__term=current_term,
                student__in=active_students,
                student__classroom=F("assessment__classroom"),
            )
            .values("student_id")
            .annotate(
                total_score=Sum("score"),
                total_max_score=Sum("assessment__max_score"),
            )
        )

        for item in student_grade_stats:

            total_max = item["total_max_score"]

            if not total_max:
                continue

            percentage = (
                float(item["total_score"])
                / float(total_max)
            ) * 100

            if percentage < LOW_ACADEMIC_THRESHOLD:
                low_academic_student_ids.add(
                    item["student_id"]
                )

    # ------------------------------------------------------------
    # Low attendance
    # ------------------------------------------------------------

    if current_term:

        # Notice that there is deliberately NO classroom filter here.
        #
        # Attendance belongs to the student and term.
        # If the student changes classroom, their earlier attendance
        # must still remain part of their attendance percentage.
        attendance_stats = (
            Attendance.objects
            .filter(
                school=school,
                term=current_term,
                student__in=active_students,
            )
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

        for item in attendance_stats:

            total_days = item["total_days"]

            if not total_days:
                continue

            percentage = (
                item["attended_days"]
                / total_days
            ) * 100

            if percentage < LOW_ATTENDANCE_THRESHOLD:
                low_attendance_student_ids.add(
                    item["student_id"]
                )

    # A student may be in both groups.
    students_needing_attention_ids = (
        low_academic_student_ids
        | low_attendance_student_ids
    )

    students_needing_attention = len(
        students_needing_attention_ids
    )

    low_academic_count = len(
        low_academic_student_ids
    )

    low_attendance_count = len(
        low_attendance_student_ids
    )

    # ============================================================
    # ATTENDANCE TREND - LAST 30 DAYS
    # ============================================================

    attendance_chart_labels = []
    attendance_chart_values = []

    start_date = today - timedelta(days=29)

    attendance_trend_records = Attendance.objects.filter(
        school=school,
        date__range=[
            start_date,
            today,
        ],
    )

    if current_term:
        attendance_trend_records = attendance_trend_records.filter(
            term=current_term,
        )

    attendance_trend = (
        attendance_trend_records
        .values("date")
        .annotate(
            total=Count("id"),
            attended=Count(
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
        .order_by("date")
    )

    attendance_by_date = {
        item["date"]: item
        for item in attendance_trend
    }

    # We include only days that actually have attendance records.
    # This avoids displaying weekends / holidays as 0% attendance.
    for day_offset in range(30):

        current_date = start_date + timedelta(
            days=day_offset
        )

        data = attendance_by_date.get(
            current_date
        )

        if not data:
            continue

        total = data["total"]
        attended = data["attended"]

        if not total:
            continue

        percentage = round(
            (attended / total) * 100,
            1,
        )

        attendance_chart_labels.append(
            current_date.strftime("%d/%m")
        )

        attendance_chart_values.append(
            percentage
        )

    # ============================================================
    # CLASSROOM ACADEMIC PERFORMANCE
    # ============================================================

    classroom_chart_labels = []
    classroom_chart_values = []

    if current_term:

        for classroom in classrooms:

            classroom_grades = Grade.objects.filter(
                school=school,
                assessment__term=current_term,
                assessment__classroom=classroom,
                student__classroom=classroom,
                student__is_active=True,
            )

            totals = classroom_grades.aggregate(
                total_score=Sum("score"),
                total_max_score=Sum(
                    "assessment__max_score"
                ),
            )

            class_total_score = totals[
                "total_score"
            ]

            class_total_max = totals[
                "total_max_score"
            ]

            if not class_total_max:
                continue

            class_percentage = round(
                (
                    float(class_total_score)
                    / float(class_total_max)
                ) * 100,
                1,
            )

            classroom_chart_labels.append(
                f"الصف {classroom.grade_level} - {classroom.name}"
            )

            classroom_chart_values.append(
                class_percentage
            )

    # ============================================================
    # CONTEXT
    # ============================================================

    context = {
        # Academic period
        "current_year": current_year,
        "current_term": current_term,

        # Main cards
        "total_students": total_students,
        "total_teachers": total_teachers,
        "total_classes": total_classes,

        # Attendance today
        "attendance_today_percentage": attendance_today_percentage,
        "today_present": today_present,
        "today_absent": today_absent,
        "today_recorded": today_recorded,
        "attendance_not_recorded": attendance_not_recorded,

        # Academic performance
        "academic_average": academic_average,
        "performance_terms": performance_terms,
        "selected_performance_term": selected_performance_term,
        "performance_is_year": performance_is_year,

        # Attention
        "students_needing_attention": students_needing_attention,
        "low_academic_count": low_academic_count,
        "low_attendance_count": low_attendance_count,

        # Thresholds
        "low_academic_threshold": LOW_ACADEMIC_THRESHOLD,
        "low_attendance_threshold": LOW_ATTENDANCE_THRESHOLD,

        # Charts
        "attendance_chart_labels": attendance_chart_labels,
        "attendance_chart_values": attendance_chart_values,

        "classroom_chart_labels": classroom_chart_labels,
        "classroom_chart_values": classroom_chart_values,
    }

    return render(
        request,
        "schools/dashboard.html",
        context,
    )

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
        # Match individual fields as before, but also support a full name
        # such as "Ahmed Mohamed" even though first/last name are stored
        # in separate columns. StudentProfile names are the source of truth.
        name_parts = query.split()
        name_query = Q(first_name__icontains=query) | Q(last_name__icontains=query)
        user_name_query = Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
        if len(name_parts) >= 2:
            first_part = name_parts[0]
            last_part = " ".join(name_parts[1:])
            name_query |= Q(first_name__icontains=first_part, last_name__icontains=last_part)
            user_name_query |= Q(user__first_name__icontains=first_part, user__last_name__icontains=last_part)

        students = students.filter(
            name_query
            | user_name_query
            | Q(user__username__icontains=query)
            | Q(student_number__icontains=query)
            | Q(parent_phone__icontains=query)
            | Q(nationality__icontains=query)
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

    if student.user_id:
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

            if user:
                user.delete()
        messages.success(request, "تم حذف الطالب بنجاح.")
        return redirect("manager:student_list")

    return render(
        request,
        "schools/students/student_confirm_delete.html",
        {"student": student},
    )




@school_admin_required
def student_academic_history(request, pk):
    school = request.user.school
    student = get_object_or_404(StudentProfile, pk=pk, school=school)
    enrollments = StudentEnrollment.objects.filter(
        school=school, student=student
    ).select_related("academic_year", "classroom").order_by("-academic_year__start_date")

    selected = None
    year_id = request.GET.get("year", "").strip()
    if year_id:
        selected = enrollments.filter(academic_year_id=year_id).first()
    if selected is None:
        selected = enrollments.first()

    subjects = []
    annual_result = None
    attendance_records = Attendance.objects.none()
    attendance_stats = None
    if selected:
        subjects = student_subject_breakdown(
            student, selected.academic_year, classroom=selected.classroom
        )
        annual_result = student_year_result(
            student, selected.academic_year, classroom=selected.classroom
        )
        attendance_records = Attendance.objects.filter(
            school=school, student=student, term__academic_year=selected.academic_year
        ).order_by("-date")
        total = attendance_records.count()
        attended = attendance_records.filter(
            status__in=[Attendance.Status.PRESENT, Attendance.Status.LATE, Attendance.Status.EXCUSED]
        ).count()
        attendance_stats = {
            "total": total,
            "present": attendance_records.filter(status=Attendance.Status.PRESENT).count(),
            "absent": attendance_records.filter(status=Attendance.Status.ABSENT).count(),
            "late": attendance_records.filter(status=Attendance.Status.LATE).count(),
            "excused": attendance_records.filter(status=Attendance.Status.EXCUSED).count(),
            "percentage": round(attended / total * 100, 1) if total else None,
        }

    return render(request, "schools/students/student_academic_history.html", {
        "student": student, "enrollments": enrollments, "selected_enrollment": selected,
        "subjects": subjects, "annual_result": annual_result,
        "attendance_records": attendance_records[:30], "attendance_stats": attendance_stats,
    })

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

    has_history = (
        Assessment.objects.filter(school=year.school, term__academic_year=year).exists()
        or Attendance.objects.filter(school=year.school, term__academic_year=year).exists()
    )
    if has_history and not year.is_current:
        messages.error(request, "لا يمكن تعديل عام دراسي تاريخي يحتوي على سجلات أكاديمية.")
        return redirect("manager:academic_year_list")

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
def academic_year_change_current(request, pk):
    school = request.user.school

    new_year = get_object_or_404(
        AcademicYear,
        pk=pk,
        school=school,
    )

    current_year = (
        AcademicYear.objects
        .filter(
            school=school,
            is_current=True,
        )
        .first()
    )

    # العام المحدد هو الحالي بالفعل
    if new_year.is_current:
        messages.info(
            request,
            "هذا العام الدراسي هو العام الحالي بالفعل.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    if request.method == "POST":

        confirmation = request.POST.get(
            "confirmation",
            "",
        ).strip()

        if confirmation != "تغيير العام":
            messages.error(
                request,
                'للتأكيد، يرجى كتابة "تغيير العام" بشكل صحيح.',
            )

        else:
            # إلغاء حالة "الحالي" من العام السابق
            if current_year:
                current_year.is_current = False
                current_year.save(
                    update_fields=["is_current"]
                )

            # مهم جداً:
            # لا نريد أن يبقى ترم من العام السابق
            # هو الترم الحالي بعد تغيير العام.
            Term.objects.filter(
                school=school,
                is_current=True,
            ).update(
                is_current=False,
                is_closed=True,
            )

            # جعل العام الجديد هو العام الحالي
            new_year.is_current = True
            new_year.save(
                update_fields=["is_current"]
            )

            messages.success(
                request,
                (
                    f"تم تغيير العام الدراسي الحالي إلى "
                    f"{new_year.name} بنجاح. "
                    "يرجى الآن تحديد الترم الحالي لهذا العام."
                ),
            )

            return redirect(
                "manager:academic_year_list"
            )

    return render(
        request,
        "schools/academic/year_change_current.html",
        {
            "current_year": current_year,
            "new_year": new_year,
        },
    )


@school_admin_required
def academic_year_delete(request, pk):
    year = get_object_or_404(
        AcademicYear,
        pk=pk,
        school=request.user.school,
    )

    # لا يمكن حذف العام الدراسي الحالي
    if year.is_current:
        messages.error(
            request,
            "لا يمكن حذف العام الدراسي الحالي. قم بتغيير العام الدراسي الحالي أولاً.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن حذف عام يحتوي على ترمات
    if year.terms.exists():
        messages.error(
            request,
            "لا يمكن حذف هذا العام الدراسي لأنه يحتوي على ترمات محفوظة.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن حذف عام يحتوي على فصول
    if year.classrooms.exists():
        messages.error(
            request,
            "لا يمكن حذف هذا العام الدراسي لأنه يحتوي على فصول محفوظة.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # العام فارغ تماماً ويمكن حذفه
    if request.method == "POST":
        year.delete()

        messages.success(
            request,
            "تم حذف العام الدراسي بنجاح.",
        )

        return redirect(
            "manager:academic_year_list"
        )

    return render(
        request,
        "schools/academic/year_confirm_delete.html",
        {
            "year": year,
        },
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

    has_history = (
        Assessment.objects.filter(school=term.school, term=term).exists()
        or Attendance.objects.filter(school=term.school, term=term).exists()
    )
    if has_history and term.is_closed:
        messages.error(request, "لا يمكن تعديل ترم مغلق يحتوي على سجلات أكاديمية.")
        return redirect("manager:academic_year_list")

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
def term_change_current(request, pk):
    school = request.user.school

    # الترم الذي يريد المدير جعله حالياً
    new_term = get_object_or_404(
        Term.objects.select_related("academic_year"),
        pk=pk,
        school=school,
    )

    # العام الدراسي الحالي
    current_year = (
        AcademicYear.objects
        .filter(
            school=school,
            is_current=True,
        )
        .first()
    )

    # يجب وجود عام دراسي حالي أولاً
    if not current_year:
        messages.error(
            request,
            "لا يوجد عام دراسي حالي. يرجى تحديد العام الدراسي الحالي أولاً.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن اختيار ترم من عام دراسي آخر
    if new_term.academic_year_id != current_year.id:
        messages.error(
            request,
            "لا يمكن جعل هذا الترم حالياً لأنه لا يتبع العام الدراسي الحالي.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # البحث عن الترم الحالي
    current_term = (
        Term.objects
        .filter(
            school=school,
            is_current=True,
        )
        .select_related("academic_year")
        .first()
    )

    # إذا كان الترم هو الحالي بالفعل
    if new_term.is_current:
        messages.info(
            request,
            "هذا الترم هو الترم الحالي بالفعل.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن إعادة فتح ترم مغلق بهذه الطريقة
    if new_term.is_closed:
        messages.error(
            request,
            "لا يمكن جعل ترم مغلق هو الترم الحالي.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    if request.method == "POST":
        confirmation = request.POST.get(
            "confirmation",
            "",
        ).strip()

        if confirmation != "تغيير الترم":
            messages.error(
                request,
                'للتأكيد، يرجى كتابة "تغيير الترم" بشكل صحيح.',
            )

        else:
            # إغلاق الترم الحالي السابق
            if current_term:
                current_term.is_current = False
                current_term.is_closed = True
                current_term.save(
                    update_fields=[
                        "is_current",
                        "is_closed",
                    ]
                )

            # جعل الترم الجديد هو الترم الحالي
            new_term.is_current = True
            new_term.is_closed = False
            new_term.save(
                update_fields=[
                    "is_current",
                    "is_closed",
                ]
            )

            messages.success(
                request,
                f"تم تغيير الترم الحالي إلى {new_term.name} بنجاح.",
            )

            return redirect(
                "manager:academic_year_list"
            )

    return render(
        request,
        "schools/academic/term_change_current.html",
        {
            "current_term": current_term,
            "current_year": current_year,
            "new_term": new_term,
        },
    )
@school_admin_required
def term_delete(request, pk):
    term = get_object_or_404(
        Term,
        pk=pk,
        school=request.user.school,
    )

    # لا يمكن حذف الترم الحالي
    if term.is_current:
        messages.error(
            request,
            "لا يمكن حذف الترم الحالي. قم بتغيير الترم الحالي أولاً.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن حذف ترم يحتوي على تقييمات
    if term.assessments.exists():
        messages.error(
            request,
            "لا يمكن حذف هذا الترم لأنه يحتوي على تقييمات أو درجات محفوظة.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # لا يمكن حذف ترم يحتوي على سجلات حضور
    if term.attendance_records.exists():
        messages.error(
            request,
            "لا يمكن حذف هذا الترم لأنه يحتوي على سجلات حضور محفوظة.",
        )
        return redirect(
            "manager:academic_year_list"
        )

    # إذا وصلنا هنا فالترم فارغ ويمكن حذفه بأمان
    if request.method == "POST":
        term.delete()

        messages.success(
            request,
            "تم حذف الترم بنجاح.",
        )

        return redirect(
            "manager:academic_year_list"
        )

    return render(
        request,
        "schools/academic/term_confirm_delete.html",
        {
            "term": term,
        },
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

    # Attendance follows the student across classroom changes.  Keep this
    # consistent with the student detail pages and certificate calculator.
    attendance_records = Attendance.objects.filter(
        school=school,
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

    # Attendance follows the student across classroom changes.  Keep this
    # consistent with the student detail pages and certificate calculator.
    attendance_records = Attendance.objects.filter(
        school=school,
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
        
    )

    total_attendance = attendance_records.count()

    present_attendance = attendance_records.filter(status=Attendance.Status.PRESENT).count()
    absent_attendance = attendance_records.filter(status=Attendance.Status.ABSENT).count()
    late_attendance = attendance_records.filter(status=Attendance.Status.LATE).count()
    excused_attendance = attendance_records.filter(status=Attendance.Status.EXCUSED).count()
    attended_attendance = present_attendance + late_attendance + excused_attendance

    attendance_percentage = None

    if total_attendance:
        attendance_percentage = round(
            (attended_attendance / total_attendance) * 100,
            1,
        )

    # -------------------------
    # Academic results - terms stay separate, annual result is derived
    # -------------------------
    academic_year = classroom.academic_year
    subjects = student_subject_breakdown(
        student, academic_year, classroom=classroom
    )
    annual_result = student_year_result(
        student, academic_year, classroom=classroom
    )
    performance_percentage = (
        round(float(annual_result["percentage"]), 1)
        if annual_result["percentage"] is not None else None
    )

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
        "present_attendance": present_attendance,
        "absent_attendance": absent_attendance,
        "late_attendance": late_attendance,
        "excused_attendance": excused_attendance,

        "performance_percentage": performance_percentage,

        "subjects": subjects,
    }

    return render(
        request,
        "schools/teacher/student_detail.html",
        context,
    )

@teacher_required
def teacher_student_subject_detail(request, student_id, assignment_id):
    teacher = request.user
    school = teacher.school

    # ---------------------------------------------------------
    # Get the teacher's assignment
    # ---------------------------------------------------------

    assignment = get_object_or_404(
        TeachingAssignment.objects
        .select_related(
            "classroom",
            "classroom__academic_year",
            "subject",
        ),
        pk=assignment_id,
        school=school,
        teacher=teacher,
    )

    classroom = assignment.classroom
    subject = assignment.subject

    # ---------------------------------------------------------
    # Get student
    # ---------------------------------------------------------

    student = get_object_or_404(
        StudentProfile.objects
        .select_related(
            "user",
            "classroom",
            "classroom__academic_year",
        ),
        pk=student_id,
        school=school,
        classroom=classroom,
        is_active=True,
    )

    # ---------------------------------------------------------
    # Attendance
    #
    # Attendance is class-level in your current system,
    # so the teacher can see this student's attendance for
    # the class they teach.
    # ---------------------------------------------------------

    attendance_records = Attendance.objects.filter(
        school=school,
        student=student,
        
    )

    total_attendance = attendance_records.count()

    present_attendance = attendance_records.filter(status=Attendance.Status.PRESENT).count()
    absent_attendance = attendance_records.filter(status=Attendance.Status.ABSENT).count()
    late_attendance = attendance_records.filter(status=Attendance.Status.LATE).count()
    excused_attendance = attendance_records.filter(status=Attendance.Status.EXCUSED).count()
    attended_attendance = present_attendance + late_attendance + excused_attendance

    attendance_percentage = None

    if total_attendance:
        attendance_percentage = round(
            (attended_attendance / total_attendance) * 100,
            1,
        )

    # ---------------------------------------------------------
    # Grades - THIS SUBJECT ONLY
    # ---------------------------------------------------------

    grades = (
        Grade.objects
        .filter(
            school=school,
            student=student,
            assessment__classroom=classroom,
            assessment__subject=subject,
        )
        .select_related(
            "assessment",
            "assessment__subject",
            "assessment__term",
        )
        .order_by(
            "-assessment__date",
            "-assessment__id",
        )
    )

    # ---------------------------------------------------------
    # Subject performance
    # ---------------------------------------------------------

    total_score = grades.aggregate(
        total=Sum("score")
    )["total"]

    total_max_score = grades.aggregate(
        total=Sum("assessment__max_score")
    )["total"]

    performance_percentage = None

    if total_max_score:
        performance_percentage = round(
            (
                float(total_score)
                / float(total_max_score)
            ) * 100,
            1,
        )

    # ---------------------------------------------------------
    # Age
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------

    context = {
        "student": student,
        "classroom": classroom,
        "subject": subject,
        "assignment": assignment,
        "age": age,

        "attendance_percentage": attendance_percentage,
        "total_attendance": total_attendance,
        "attended_attendance": attended_attendance,
        "present_attendance": present_attendance,
        "absent_attendance": absent_attendance,
        "late_attendance": late_attendance,
        "excused_attendance": excused_attendance,

        "performance_percentage": performance_percentage,

        "grades": grades,
    }

    return render(
        request,
        "schools/teacher/student_subject_detail.html",
        context,
    )