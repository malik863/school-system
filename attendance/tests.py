import json
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from academics.models import Classroom
from attendance.models import Attendance
from schools.models import AcademicYear, School, Term
from students.models import StudentProfile


class OfflineAttendanceSyncTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.school = School.objects.create(name="Offline School", slug="offline-school")
        self.teacher = User.objects.create_user(
            username="teacher", password="pass12345", role=User.Role.TEACHER, school=self.school
        )
        self.other_teacher = User.objects.create_user(
            username="other", password="pass12345", role=User.Role.TEACHER, school=self.school
        )
        self.year = AcademicYear.objects.create(
            school=self.school, name="2026/2027", start_date=date(2026, 9, 1), end_date=date(2027, 6, 30)
        )
        self.term = Term.objects.create(
            school=self.school, academic_year=self.year, name="Term 1",
            start_date=date(2026, 9, 1), end_date=date(2027, 1, 15), is_current=True,
        )
        self.classroom = Classroom.objects.create(
            school=self.school, academic_year=self.year, name="A", grade_level=1, lead_teacher=self.teacher
        )
        self.student = StudentProfile.objects.create(
            school=self.school, first_name="Ahmed", classroom=self.classroom
        )
        self.url = reverse("teacher:attendance_offline_sync")
        self.client.force_login(self.teacher)

    def payload(self, status="present", baseline=""):
        return {
            "classroom_id": self.classroom.pk,
            "date": "2026-10-05",
            "records": [{"student_id": self.student.pk, "status": status, "baseline": baseline}],
        }

    def post(self, payload):
        return self.client.post(self.url, data=json.dumps(payload), content_type="application/json")

    def test_offline_sync_saves_valid_attendance(self):
        response = self.post(self.payload())
        self.assertEqual(response.status_code, 200)
        record = Attendance.objects.get(student=self.student, date=date(2026, 10, 5))
        self.assertEqual(record.status, Attendance.Status.PRESENT)
        self.assertEqual(record.recorded_by, self.teacher)

    def test_offline_sync_does_not_silently_overwrite_conflict(self):
        Attendance.objects.create(
            school=self.school, student=self.student, classroom=self.classroom, term=self.term,
            date=date(2026, 10, 5), status=Attendance.Status.ABSENT, recorded_by=self.teacher,
        )
        response = self.post(self.payload(status="late", baseline="present"))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Attendance.objects.get(student=self.student, date=date(2026, 10, 5)).status, "absent")

    def test_teacher_cannot_sync_another_teachers_class(self):
        self.classroom.lead_teacher = self.other_teacher
        self.classroom.save()
        response = self.post(self.payload())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Attendance.objects.filter(student=self.student).exists())

    def test_closed_term_rejects_offline_sync(self):
        self.term.is_closed = True
        self.term.is_current = False
        self.term.save()
        response = self.post(self.payload())
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Attendance.objects.filter(student=self.student).exists())
