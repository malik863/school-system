from datetime import datetime, timedelta
import json

from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
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
                is_active=True,
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

            elif term.is_closed:

                form.add_error(
                    "date",
                    "لا يمكن تعديل الحضور داخل ترم مغلق.",
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
                        is_active=True,
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
    # Date navigation / week history
    # ---------------------------------------------------------
    previous_date = selected_date - timedelta(days=1)
    next_date = selected_date + timedelta(days=1)
    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_dates = [week_start + timedelta(days=i) for i in range(7)]

    # Make it obvious whether attendance was actually recorded.
    recorded_count = len(initial_attendance)
    student_count = students.count() if selected_classroom else 0
    attendance_state = (
        "complete" if student_count and recorded_count == student_count
        else "partial" if recorded_count
        else "empty"
    )

    week_recorded_dates = set()
    if selected_classroom:
        week_recorded_dates = set(
            Attendance.objects.filter(
                school=school,
                classroom=selected_classroom,
                date__range=(week_dates[0], week_dates[-1]),
            ).values_list("date", flat=True).distinct()
        )
    week_days = [
        {"date": day, "has_records": day in week_recorded_dates}
        for day in week_dates
    ]

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
            "previous_date": previous_date,
            "next_date": next_date,
            "week_dates": week_dates,
            "week_days": week_days,
            "recorded_count": recorded_count,
            "student_count": student_count,
            "attendance_state": attendance_state,
            "today": timezone.localdate(),
        },
    )

@teacher_required
@require_POST
def offline_attendance_sync(request):
    """Safely accept attendance captured while a teacher was offline.

    The browser sends the status it originally saw (baseline). If the server
    changed since then, the batch is rejected instead of silently overwriting.
    """
    teacher = request.user
    school = teacher.school

    try:
        payload = json.loads(request.body.decode("utf-8"))
        classroom_id = int(payload.get("classroom_id"))
        selected_date = datetime.strptime(payload.get("date", ""), "%Y-%m-%d").date()
        records = payload.get("records") or []
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"error": "بيانات المزامنة غير صالحة."}, status=400)

    try:
        classroom = Classroom.objects.select_related("academic_year").get(
            pk=classroom_id, school=school, lead_teacher=teacher
        )
    except Classroom.DoesNotExist:
        return JsonResponse({"error": "لا يمكنك تسجيل حضور هذا الفصل."}, status=403)

    term = Term.objects.filter(
        school=school,
        academic_year=classroom.academic_year,
        start_date__lte=selected_date,
        end_date__gte=selected_date,
    ).order_by("-start_date").first()
    if not term:
        return JsonResponse({"error": "لا يوجد ترم يغطي هذا التاريخ."}, status=400)
    if term.is_closed:
        return JsonResponse({"error": "لا يمكن مزامنة حضور داخل ترم مغلق."}, status=400)

    allowed_statuses = {choice for choice, _ in Attendance.Status.choices}
    student_ids = []
    normalized = []
    for row in records:
        try:
            student_id = int(row.get("student_id"))
        except (TypeError, ValueError):
            return JsonResponse({"error": "رقم طالب غير صالح."}, status=400)
        status = row.get("status", "")
        baseline = row.get("baseline", "") or ""
        if status not in allowed_statuses or baseline not in allowed_statuses | {""}:
            return JsonResponse({"error": "حالة حضور غير صالحة."}, status=400)
        student_ids.append(student_id)
        normalized.append((student_id, status, baseline))

    students = {
        student.pk: student
        for student in StudentProfile.objects.filter(
            pk__in=student_ids, school=school, classroom=classroom, is_active=True
        )
    }
    if len(students) != len(set(student_ids)):
        return JsonResponse({"error": "تغيرت قائمة الطلاب أو يوجد طالب غير مصرح به."}, status=409)

    existing = {
        record.student_id: record
        for record in Attendance.objects.filter(
            school=school, classroom=classroom, date=selected_date, student_id__in=student_ids
        )
    }
    conflicts = []
    for student_id, desired, baseline in normalized:
        current = existing.get(student_id)
        current_status = current.status if current else ""
        if current_status != baseline and current_status != desired:
            conflicts.append({"student_id": student_id, "server_status": current_status})

    if conflicts:
        return JsonResponse(
            {"error": "تغير الحضور على الخادم منذ حفظ النسخة دون اتصال.", "conflicts": conflicts},
            status=409,
        )

    with transaction.atomic():
        for student_id, status, _baseline in normalized:
            Attendance.objects.update_or_create(
                student=students[student_id],
                date=selected_date,
                defaults={
                    "school": school,
                    "classroom": classroom,
                    "term": term,
                    "status": status,
                    "recorded_by": teacher,
                },
            )

    return JsonResponse({"ok": True, "saved": len(normalized)})
