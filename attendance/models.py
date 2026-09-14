

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import SchoolOwnedModel


class Attendance(SchoolOwnedModel):

    class Status(models.TextChoices):
        PRESENT = "present", "حاضر"
        ABSENT = "absent", "غائب"
        LATE = "late", "متأخر"
        EXCUSED = "excused", "بعذر"

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="الطالب",
    )

    classroom = models.ForeignKey(
        "academics.Classroom",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="الفصل",
    )

    term = models.ForeignKey(
        "schools.Term",
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name="الترم",
    )

    date = models.DateField(
        verbose_name="التاريخ",
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
        verbose_name="الحالة",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_attendance",
        verbose_name="سجلها",
    )

    class Meta:
        verbose_name = "حضور"
        verbose_name_plural = "الحضور"

        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "student",
                    "date",
                ],
                name="unique_student_attendance_per_day",
            ),
        ]

    def clean(self):
        if self.student.school_id != self.school_id:
            raise ValidationError(
                "الطالب يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.classroom.school_id != self.school_id:
            raise ValidationError(
                "الفصل يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.term.school_id != self.school_id:
            raise ValidationError(
                "الترم يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.student.classroom_id != self.classroom_id:
            raise ValidationError(
                "الطالب ليس مسجلاً في هذا الفصل."
            )

        if self.recorded_by_id:
            if self.recorded_by.school_id != self.school_id:
                raise ValidationError(
                    "مسجل الحضور يجب أن ينتمي إلى نفس المدرسة."
                )

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.date} - "
            f"{self.get_status_display()}"
        )




