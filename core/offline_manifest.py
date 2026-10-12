from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET
from academics.models import Classroom, TeachingAssignment


@login_required
@require_GET
def offline_manifest(request):
    user = request.user
    role = getattr(user, 'role', '')
    if not getattr(user, 'school_id', None):
            return JsonResponse({'urls': []}, status=403)
    if role not in ('teacher', 'school_manager'):
        return JsonResponse({'urls': []}, status=403)
    if role == 'teacher':
        urls = ['/teacher/', '/teacher/classes/', '/teacher/subjects/',
                '/teacher/assignments/', '/teacher/assessments/', '/teacher/attendance/']
        classes = Classroom.objects.filter(school=user.school, lead_teacher=user)
        today = timezone.localdate().isoformat()
        for classroom in classes:
            urls.append(f'/teacher/classes/{classroom.pk}/')
            urls.append(f'/teacher/attendance/?classroom={classroom.pk}&date={today}')
        assignment_ids = TeachingAssignment.objects.filter(school=user.school, teacher=user).values_list('pk', flat=True)
        for assignment_id in assignment_ids:
            urls.append(f'/teacher/subjects/{assignment_id}/')
    else:
        urls = ['/manager/', '/manager/students/', '/manager/teachers/',
                '/manager/classes/', '/manager/subjects/', '/manager/assignments/',
                '/manager/academic/', '/manager/grade-schemes/']
    return JsonResponse({'urls': urls[:200]})
