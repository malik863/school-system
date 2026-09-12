
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import SchoolOwnedModel


class StudentProfile(SchoolOwnedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
        verbose_name="حساب الطالب",
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
        return (
            self.user.get_full_name()
            or self.user.username
        )





