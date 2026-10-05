from datetime import date
from django.core.exceptions import ValidationError
from django.test import TestCase

from schools.models import School, AcademicYear, Term


class AcademicPeriodIntegrityTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School", slug="test-school")
        self.year = AcademicYear.objects.create(
            school=self.school, name="2026/2027",
            start_date=date(2026, 9, 1), end_date=date(2027, 6, 30), is_current=True,
        )

    def test_term_must_be_inside_academic_year(self):
        term = Term(
            school=self.school, academic_year=self.year, name="Bad term",
            start_date=date(2026, 8, 1), end_date=date(2027, 1, 15),
        )
        with self.assertRaises(ValidationError):
            term.full_clean()

    def test_only_one_current_year_per_school(self):
        second = AcademicYear.objects.create(
            school=self.school, name="2027/2028",
            start_date=date(2027, 9, 1), end_date=date(2028, 6, 30), is_current=True,
        )
        self.year.refresh_from_db()
        self.assertFalse(self.year.is_current)
        self.assertTrue(second.is_current)
