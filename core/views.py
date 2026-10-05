from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg, Sum
from django.core.exceptions import PermissionDenied, ValidationError
from django.contrib.auth import get_user_model

from .decorators import role_required
from .forms import GradeEntryForm

from academics.models import Classroom, TeachingAssignment, Subject
from students.models import StudentProfile
from schools.models import Term
from assessments.models import Grade

User = get_user_model()


@login_required
def manager_dashboard(request):
    """Compatibility URL; the actual manager dashboard lives in schools."""
    if request.user.is_school_manager:
        return redirect("manager:dashboard")
    raise PermissionDenied("الحساب الحالي ليس مدير مدرسة.")


@login_required
@role_required('teacher')
def teacher_dashboard(request):
    """Teacher Dashboard: Distinguishes between Class Manager and Subject Teacher roles."""
    teacher = request.user
    
    # Classrooms managed as Home Room Teacher (فصلي)
    managed_classrooms = Classroom.objects.filter(lead_teacher=teacher, school=teacher.school)
    
    # Subject teaching assignments (فصول أخرى)
    teaching_assignments = TeachingAssignment.objects.filter(
        teacher=teacher,
        school=teacher.school,
    ).select_related('classroom', 'subject')

    context = {
        'managed_classrooms': managed_classrooms,
        'teaching_assignments': teaching_assignments,
    }
    return render(request, 'core/dashboard_teacher.html', context)

@login_required
def student_dashboard(request):
    if not request.user.is_student:
        raise PermissionDenied("الحساب الحالي ليس طالباً.")

    profile = get_object_or_404(
        StudentProfile.objects.select_related("classroom"),
        user=request.user,
        school=request.user.school,
    )
    return render(request, "core/dashboard_student.html", {"student": profile})


@login_required
@role_required('teacher')
def enter_grades(request, classroom_id):
    classroom = get_object_or_404(Classroom, id=classroom_id)
    teacher = request.user

    if request.method == 'POST':
        form = GradeEntryForm(request.POST, classroom=classroom, teacher=teacher)
        if form.is_valid():
            grade = form.save(commit=False)
            
            # 1. Assign the school tenant from the classroom or teacher
            grade.school = classroom.school  
            
            # 2. Assign the user who recorded the grade
            grade.recorded_by = teacher
            
            try:
                grade.save()
                messages.success(request, f"تم تسجيل درجة {grade.student.get_full_name()} بنجاح.")
                return redirect('enter_grades', classroom_id=classroom.id)
            except ValidationError as e:
                form.add_error(None, e.message)
    else:
        form = GradeEntryForm(classroom=classroom, teacher=teacher)

    # Fetch recent grades for this classroom
    recent_grades = Grade.objects.filter(
        student__student_profile__classroom=classroom
    ).select_related('student', 'subject', 'term').order_by('-date')[:15]

    context = {
        'classroom': classroom,
        'form': form,
        'recent_grades': recent_grades,
    }
    return render(request, 'core/enter_grades.html', context)
"""
@login_required
def student_dashboard(request):
    if not request.user.is_student:
        raise PermissionDenied("الحساب الحالي ليس طالباً.")

    profile = get_object_or_404(
        StudentProfile.objects.select_related("classroom"),
        user=request.user,
        school=request.user.school,
    )
    return render(request, "core/dashboard_student.html", {"student": profile})


@login_required
@role_required('teacher')
def enter_grades(request, classroom_id):

    classroom = get_object_or_404(Classroom, id=classroom_id)
    
    if request.method == 'POST':
        form = GradeEntryForm(request.POST, classroom=classroom, teacher=request.user)
        if form.is_valid():
            grade = form.save(commit=False)
            grade.school = request.user.school
            grade.recorded_by = request.user
            
            try:
                grade.save()
                messages.success(request, f"تم تسجيل درجة {grade.student.get_full_name()} بنجاح.")
                return redirect('enter_grades', classroom_id=classroom.id)
            except ValidationError as e:
                form.add_error(None, e.message)
    else:
        form = GradeEntryForm(classroom=classroom, teacher=request.user)

    # Fetch recent grades entered for this classroom
    recent_grades = Grade.objects.filter(
        student__student_profile__classroom=classroom
    ).select_related('student', 'subject', 'term').order_by('-date')[:15]

    context = {
        'classroom': classroom,
        'form': form,
        'recent_grades': recent_grades,
    }
    return render(request, 'core/enter_grades.html', context)

    """
@login_required
def student_report_card(request, student_id):
    # Get student profile and the user object
    student_profile = get_object_or_404(StudentProfile, id=student_id)
    student_user = student_profile.user  # <--- THIS IS THE USER INSTANCE

    active_term = Term.objects.filter(is_current=True).first()

    if not active_term:
        messages.error(request, "لا يوجد فصل دراسي حالي نشط.")
        return redirect('manager_dashboard')

    # Query Grade using student_user (User model instance)
    student_grades = Grade.objects.filter(student=student_user, term=active_term)

    subjects_summary = []
    subject_ids = student_grades.values_list('subject_id', flat=True).distinct()
    subjects = Subject.objects.filter(id__in=subject_ids)

    total_obtained = 0.0
    total_possible = 0.0

    for subject in subjects:
        subject_grades = student_grades.filter(subject=subject)
        score_sum = subject_grades.aggregate(s=Sum('score'))['s'] or 0.0
        max_sum = subject_grades.aggregate(m=Sum('max_score'))['m'] or 0.0

        percentage = round((score_sum / max_sum * 100), 1) if max_sum > 0 else 0.0

        total_obtained += score_sum
        total_possible += max_sum

        subjects_summary.append({
            'subject': subject,
            'obtained': score_sum,
            'max': max_sum,
            'percentage': percentage,
            'is_passing': percentage >= 50.0,
            'details': subject_grades,
        })

    overall_percentage = round((total_obtained / total_possible * 100), 1) if total_possible > 0 else 0.0

    context = {
        'student_profile': student_profile,
        'student_user': student_user,
        'active_term': active_term,
        'subjects_summary': subjects_summary,
        'total_obtained': total_obtained,
        'total_possible': total_possible,
        'overall_percentage': overall_percentage,
    }
    return render(request, 'core/report_card.html', context)