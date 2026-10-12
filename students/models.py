
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import SchoolOwnedModel


class StudentProfile(SchoolOwnedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        null=True,
        blank=True,
        verbose_name="حساب الطالب",
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="الاسم الأول",
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="اسم العائلة",
    )

    classroom = models.ForeignKey(
        "academics.Classroom",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="students",
        verbose_name="الفصل",
    )

    student_number = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="رقم الطالب",
    )

    national_id = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="الرقم القومي",
    )

    nationality = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="الجنسية",
    )

    parent_phone = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="رقم ولي الأمر",
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ الميلاد",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="الطالب نشط",
    )

    class Meta:
        verbose_name = "طالب"
        verbose_name_plural = "الطلاب"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "student_number",
                ],
                condition=~models.Q(student_number=""),
                name="unique_student_number_per_school",
            ),
        ]

    def clean(self):
        if self.user_id:
            if self.user.school_id != self.school_id:
                raise ValidationError(
                    "حساب الطالب يجب أن ينتمي إلى نفس المدرسة."
                )

        if self.classroom_id:
            if self.classroom.school_id != self.school_id:
                raise ValidationError(
                    "فصل الطالب يجب أن ينتمي إلى نفس المدرسة."
                )

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()

        if full_name:
            return full_name

        return f"Student {self.student_number}"






class StudentEnrollment(SchoolOwnedModel):
    """Historical classroom membership for a student in an academic year."""
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name="enrollments", verbose_name="الطالب"
    )
    academic_year = models.ForeignKey(
        "schools.AcademicYear", on_delete=models.PROTECT, related_name="student_enrollments", verbose_name="العام الدراسي"
    )
    classroom = models.ForeignKey(
        "academics.Classroom", on_delete=models.PROTECT, related_name="student_enrollments", verbose_name="الفصل"
    )

    class Meta:
        verbose_name = "قيد طالب"
        verbose_name_plural = "قيود الطلاب"
        ordering = ["-academic_year__start_date", "student_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "academic_year"],
                name="unique_student_enrollment_per_year",
            )
        ]

    def clean(self):
        if self.student_id and self.student.school_id != self.school_id:
            raise ValidationError("الطالب يجب أن ينتمي إلى نفس المدرسة.")
        if self.academic_year_id and self.academic_year.school_id != self.school_id:
            raise ValidationError("العام الدراسي يجب أن ينتمي إلى نفس المدرسة.")
        if self.classroom_id:
            if self.classroom.school_id != self.school_id:
                raise ValidationError("الفصل يجب أن ينتمي إلى نفس المدرسة.")
            if self.academic_year_id and self.classroom.academic_year_id != self.academic_year_id:
                raise ValidationError("الفصل يجب أن ينتمي إلى نفس العام الدراسي للقيد.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student} - {self.academic_year} - {self.classroom}"
