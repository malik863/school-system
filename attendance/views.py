from datetime import datetime

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.utils import timezone

from academics.models import Classroom
from schools.decorators import teacher_required
from schools.models import Term
from students.models import StudentProfile

from .forms import AttendanceForm
from .models import Attendance


@teacher_required
def teacher_attendance(request):

    teacher = request.user
    school = teacher.school

    # ---------------------------------------------------------
    # ONLY classes where this teacher is the lead teacher
    # ---------------------------------------------------------

    classrooms = (
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

    selected_classroom = None

    students = StudentProfile.objects.none()

    initial_attendance = {}

    # ---------------------------------------------------------
    # Get selected classroom and date
    # ---------------------------------------------------------

    classroom_id = (
        request.GET.get("classroom")
        or request.POST.get("classroom")
    )

    date_value = (
        request.GET.get("date")
        or request.POST.get("date")
    )

    if date_value:

        try:
            selected_date = datetime.strptime(
                date_value,
                "%Y-%m-%d",
            ).date()

        except (ValueError, TypeError):

            selected_date = timezone.localdate()

    else:

        selected_date = timezone.localdate()

    # ---------------------------------------------------------
    # Find selected classroom
    # ---------------------------------------------------------

    if classroom_id:

        try:

            selected_classroom = classrooms.get(
                pk=classroom_id
            )

        except Classroom.DoesNotExist:

            messages.error(
                request,
                "لا يمكنك الوصول إلى هذا الفصل.",
            )

            return redirect(
                "attendance:teacher_attendance"
            )

    # ---------------------------------------------------------
    # Load students
    # ---------------------------------------------------------

    if selected_classroom:

        students = (
            StudentProfile.objects
            .filter(
                school=school,
                classroom=selected_classroom,
                user__is_active=True,
            )
            .select_related("user")
            .order_by(
                "user__first_name",
                "user__last_name",
            )
        )

        existing_records = (
            Attendance.objects
            .filter(
                school=school,
                classroom=selected_classroom,
                date=selected_date,
            )
        )

        initial_attendance = {
            record.student_id: record.status
            for record in existing_records
        }

    # =========================================================
    # POST = SAVE ATTENDANCE
    # =========================================================

    if request.method == "POST":

        if not selected_classroom:

            messages.error(
                request,
                "يرجى اختيار الفصل.",
            )

            return redirect("teacher:attendance")

        form = AttendanceForm(
            request.POST,
            teacher=teacher,
            students=students,
            initial_attendance=initial_attendance,
        )

        if form.is_valid():

            selected_classroom = form.cleaned_data[
                "classroom"
            ]

            selected_date = form.cleaned_data[
                "date"
            ]

            # -------------------------------------------------
            # Security check:
            # The teacher MUST be the lead teacher.
            # -------------------------------------------------

            if selected_classroom.lead_teacher_id != teacher.id:

                messages.error(
                    request,
                    "لا يمكنك تسجيل حضور هذا الفصل.",
                )

                return redirect("teacher:attendance")

            # -------------------------------------------------
            # Find the term covering this date
            # -------------------------------------------------

            term = (
                Term.objects
                .filter(
                    school=school,
                    academic_year=selected_classroom.academic_year,
                    start_date__lte=selected_date,
                    end_date__gte=selected_date,
                )
                .order_by("-start_date")
                .first()
            )

            if not term:

                form.add_error(
                    "date",
                    "لا يوجد ترم يغطي هذا التاريخ لهذا العام الدراسي.",
                )

            else:

                # -------------------------------------------------
                # Reload students after validation
                # -------------------------------------------------

                students = (
                    StudentProfile.objects
                    .filter(
                        school=school,
                        classroom=selected_classroom,
                        user__is_active=True,
                    )
                    .select_related("user")
                    .order_by(
                        "user__first_name",
                        "user__last_name",
                    )
                )

                # -------------------------------------------------
                # Save attendance
                # -------------------------------------------------

                with transaction.atomic():

                    for student in students:

                        field_name = (
                            f"student_{student.pk}"
                        )

                        status = form.cleaned_data.get(
                            field_name
                        )

                        if not status:
                            continue

                        Attendance.objects.update_or_create(
                            student=student,
                            date=selected_date,
                            defaults={
                                "school": school,
                                "classroom": selected_classroom,
                                "term": term,
                                "status": status,
                                "recorded_by": teacher,
                            },
                        )

                messages.success(
                    request,
                    "تم حفظ الحضور والغياب بنجاح.",
                )

                return redirect(
                    f"/teacher/attendance/"
                    f"?classroom={selected_classroom.pk}"
                    f"&date={selected_date.strftime('%Y-%m-%d')}"
                )

    # =========================================================
    # GET = DISPLAY ATTENDANCE PAGE
    # =========================================================

    else:

        form = AttendanceForm(
            teacher=teacher,
            students=students,
            initial_attendance=initial_attendance,
            initial={
                "classroom": (
                    selected_classroom.pk
                    if selected_classroom
                    else None
                ),
                "date": selected_date,
            },
        )

    # ---------------------------------------------------------
    # Render
    # ---------------------------------------------------------

    return render(
        request,
        "schools/teacher/attendance.html",
        {
            "form": form,
            "classrooms": classrooms,
            "selected_classroom": selected_classroom,
            "students": students,
            "selected_date": selected_date,
        },
    )