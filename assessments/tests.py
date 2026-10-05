from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase

from academics.models import Classroom, Subject, ClassroomSubject
from assessments.models import Assessment
from schools.models import School, AcademicYear, Term


class AssessmentPeriodIntegrityTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="School", slug="assessment-school")
        self.y1 = AcademicYear.objects.create(school=self.school, name="Y1", start_date=date(2026,9,1), end_date=date(2027,6,30))
        self.y2 = AcademicYear.objects.create(school=self.school, name="Y2", start_date=date(2027,9,1), end_date=date(2028,6,30))
        self.term = Term.objects.create(school=self.school, academic_year=self.y1, name="T1", start_date=date(2026,9,1), end_date=date(2027,1,15))
        self.c1 = Classroom.objects.create(school=self.school, academic_year=self.y1, name="A", grade_level=1)
        self.c2 = Classroom.objects.create(school=self.school, academic_year=self.y2, name="B", grade_level=2)
        self.subject = Subject.objects.create(school=self.school, name="Math")
        ClassroomSubject.objects.create(school=self.school, classroom=self.c1, subject=self.subject)
        ClassroomSubject.objects.create(school=self.school, classroom=self.c2, subject=self.subject)

    def assessment(self, classroom, assessment_date):
        return Assessment(school=self.school, classroom=classroom, subject=self.subject, term=self.term, title="Exam", assessment_type="exam", max_score=10, date=assessment_date)

    def test_rejects_cross_year_classroom_and_term(self):
        with self.assertRaises(ValidationError):
            self.assessment(self.c2, date(2026,10,1)).full_clean()

    def test_rejects_date_outside_term(self):
        with self.assertRaises(ValidationError):
            self.assessment(self.c1, date(2027,3,1)).full_clean()
