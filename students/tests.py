from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase

from academics.models import Classroom
from schools.models import School, AcademicYear
from students.models import StudentProfile, StudentEnrollment


class StudentEnrollmentTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="School", slug="school")
        self.y1 = AcademicYear.objects.create(school=self.school, name="Y1", start_date=date(2026,9,1), end_date=date(2027,6,30))
        self.y2 = AcademicYear.objects.create(school=self.school, name="Y2", start_date=date(2027,9,1), end_date=date(2028,6,30))
        self.c1 = Classroom.objects.create(school=self.school, academic_year=self.y1, name="A", grade_level=1)
        self.c2 = Classroom.objects.create(school=self.school, academic_year=self.y2, name="A", grade_level=2)
        self.student = StudentProfile.objects.create(school=self.school, first_name="Student", classroom=self.c1)

    def test_promotion_keeps_previous_enrollment(self):
        StudentEnrollment.objects.create(school=self.school, student=self.student, academic_year=self.y1, classroom=self.c1)
        self.student.classroom = self.c2
        self.student.save()
        StudentEnrollment.objects.update_or_create(
            school=self.school, student=self.student, academic_year=self.y2,
            defaults={"classroom": self.c2},
        )
        self.assertEqual(self.student.enrollments.count(), 2)
        self.assertTrue(self.student.enrollments.filter(academic_year=self.y1, classroom=self.c1).exists())
        self.assertTrue(self.student.enrollments.filter(academic_year=self.y2, classroom=self.c2).exists())

    def test_enrollment_classroom_must_match_year(self):
        enrollment = StudentEnrollment(school=self.school, student=self.student, academic_year=self.y1, classroom=self.c2)
        with self.assertRaises(ValidationError):
            enrollment.full_clean()
