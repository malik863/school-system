

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from core.models import SchoolOwnedModel
from academics.models import ClassroomSubject


class Assessment(SchoolOwnedModel):

    class AssessmentType(models.TextChoices):
        EXAM = "exam", "اختبار"
        PROJECT = "project", "مشروع"

    classroom = models.ForeignKey(
        "academics.Classroom",
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name="الفصل",
    )

    subject = models.ForeignKey(
        "academics.Subject",
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name="المادة",
    )

    term = models.ForeignKey(
        "schools.Term",
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name="الترم",
    )

    title = models.CharField(
        max_length=150,
        verbose_name="اسم التقييم",
    )

    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        verbose_name="نوع التقييم",
    )

    max_score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
        verbose_name="الدرجة النهائية",
    )

    date = models.DateField(
        verbose_name="التاريخ",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_assessments",
        verbose_name="أنشأه",
    )

    class Meta:
        verbose_name = "تقييم"
        verbose_name_plural = "التقييمات"

        ordering = ["-date", "-id"]

    def clean(self):
        if self.classroom.school_id != self.school_id:
            raise ValidationError(
                "الفصل يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.subject.school_id != self.school_id:
            raise ValidationError(
                "المادة يجب أن تنتمي إلى نفس المدرسة."
            )

        if self.term.school_id != self.school_id:
            raise ValidationError(
                "الترم يجب أن ينتمي إلى نفس المدرسة."
            )

        if (
            self.term.academic_year_id
            and self.classroom.academic_year_id
            != self.term.academic_year_id
        ):
            raise ValidationError(
                "الفصل والترم يجب أن يكونا في نفس العام الدراسي."
            )

        if self.classroom_id and self.subject_id:
            if not ClassroomSubject.objects.filter(
                school=self.school,
                classroom=self.classroom,
                subject=self.subject,
            ).exists():
                raise ValidationError(
                    "هذه المادة غير مضافة إلى هذا الفصل."
                )

        if self.created_by_id:
            if self.created_by.school_id != self.school_id:
                raise ValidationError(
                    "منشئ التقييم يجب أن ينتمي إلى نفس المدرسة."
                )
            

    def __str__(self):
        return f"{self.title} - {self.subject}"


class Grade(SchoolOwnedModel):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name="grades",
        verbose_name="التقييم",
    )

    student = models.ForeignKey(
        "students.StudentProfile",
        on_delete=models.CASCADE,
        related_name="grades",
        verbose_name="الطالب",
    )

    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[
            MinValueValidator(0),
        ],
        verbose_name="الدرجة",
    )

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="recorded_grades",
        verbose_name="سجلها",
    )

    recorded_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        verbose_name = "درجة"
        verbose_name_plural = "الدرجات"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "assessment",
                    "student",
                ],
                name="unique_grade_per_student_assessment",
            ),
        ]

    def clean(self):
        if self.assessment.school_id != self.school_id:
            raise ValidationError(
                "التقييم يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.student.school_id != self.school_id:
            raise ValidationError(
                "الطالب يجب أن ينتمي إلى نفس المدرسة."
            )

        if self.student.classroom_id != self.assessment.classroom_id:
            raise ValidationError(
                "الطالب ليس في فصل هذا التقييم."
            )

        if self.score > self.assessment.max_score:
            raise ValidationError(
                "درجة الطالب لا يمكن أن تتجاوز الدرجة النهائية."
            )

    def __str__(self):
        return (
            f"{self.student} - "
            f"{self.assessment} - "
            f"{self.score}"
        )




