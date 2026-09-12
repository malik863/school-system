

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from core.models import SchoolOwnedModel

from decimal import Decimal

from django.db.models import Sum


class Classroom(SchoolOwnedModel):
    academic_year = models.ForeignKey(
        "schools.AcademicYear",
        on_delete=models.CASCADE,
        related_name="classrooms",
        verbose_name="العام الدراسي",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="اسم الفصل",
    )

    grade_level = models.PositiveIntegerField(
        verbose_name="الصف الدراسي",
    )

    lead_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="homeroom_classes",
        verbose_name="معلم الفصل",
    )

    class Meta:
        verbose_name = "فصل"
        verbose_name_plural = "الفصول"

        ordering = [
            "grade_level",
            "name",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "academic_year",
                    "name",
                ],
                name="unique_classroom_per_year",
            ),
        ]

    def clean(self):
        if self.academic_year_id:
            if self.school_id != self.academic_year.school_id:
                raise ValidationError(
                    "الفصل والعام الدراسي يجب أن ينتميا إلى نفس المدرسة."
                )

        if self.lead_teacher_id:
            if self.lead_teacher.school_id != self.school_id:
                raise ValidationError(
                    "معلم الفصل يجب أن ينتمي إلى نفس المدرسة."
                )

            if not self.lead_teacher.is_teacher:
                raise ValidationError(
                    "معلم الفصل يجب أن يكون معلماً."
                )

    def __str__(self):
        return f"{self.name} - الصف {self.grade_level}"


class Subject(SchoolOwnedModel):
    name = models.CharField(
        max_length=100,
        verbose_name="اسم المادة",
    )

    code = models.CharField(
        max_length=30,
        blank=True,
        verbose_name="كود المادة",
    )

    class Meta:
        verbose_name = "مادة"
        verbose_name_plural = "المواد"

        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "name",
                ],
                name="unique_subject_per_school",
            ),
        ]

    def __str__(self):
        return self.name

class TeachingAssignment(SchoolOwnedModel):
    """
    Assigns exactly one teacher to a subject in a classroom.
    """

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        verbose_name="المعلم",
    )

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        verbose_name="الفصل",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="teaching_assignments",
        verbose_name="المادة",
    )

    class Meta:
        verbose_name = "تكليف تدريسي"
        verbose_name_plural = "التكليفات التدريسية"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "classroom", "subject"],
                name="unique_classroom_subject_teacher",
            )
        ]
        ordering = ["classroom", "subject"]

    def __str__(self):
        return (
            f"{self.classroom} - "
            f"{self.subject} - "
            f"{self.teacher}"
        )

    def clean(self):
        super().clean()

        if not self.school_id:
            return

        if self.teacher_id:
            if self.teacher.school_id != self.school_id:
                raise ValidationError(
                    "المعلم يجب أن يكون تابعًا لنفس المدرسة."
                )

            if not self.teacher.is_teacher:
                raise ValidationError(
                    "المستخدم المحدد ليس معلمًا."
                )

        if self.classroom_id:
            if self.classroom.school_id != self.school_id:
                raise ValidationError(
                    "الفصل يجب أن يكون تابعًا لنفس المدرسة."
                )

        if self.subject_id:
            if self.subject.school_id != self.school_id:
                raise ValidationError(
                    "المادة يجب أن تكون تابعة لنفس المدرسة."
                )

        # The subject MUST be enabled for this classroom.
# The subject MUST be enabled for this classroom.
        if self.classroom_id and self.subject_id:

            exists = ClassroomSubject.objects.filter(
                school=self.school,
                classroom=self.classroom,
                subject=self.subject,
            ).exists()

            if not exists:
                raise ValidationError(
                    "هذه المادة غير مضافة إلى هذا الفصل. "
                    "أضف المادة إلى الفصل أولًا."
                )

            # The subject must also belong to the classroom's
            # Academic Scheme.
            scheme_exists = AcademicScheme.objects.filter(
                school=self.school,
                classrooms=self.classroom,
                subjects=self.subject,
            ).exists()

            if not scheme_exists:
                raise ValidationError(
                    "هذه المادة غير موجودة في النظام الأكاديمي لهذا الفصل."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


    
class GradeScheme(SchoolOwnedModel):
    class AssessmentType(models.TextChoices):
        EXAM = "exam", "اختبار"
        PROJECT = "project", "مشروع"

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="grade_schemes",
        verbose_name="المادة",
    )

    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        verbose_name="نوع التقييم",
    )

    max_count = models.PositiveIntegerField(
        verbose_name="عدد التقييمات",
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="الوزن",
    )

    classrooms = models.ManyToManyField(
        Classroom,
        blank=True,
        related_name="grade_schemes",
        verbose_name="الفصول",
    )

    class Meta:
        verbose_name = "نظام درجات"
        verbose_name_plural = "أنظمة الدرجات"

        constraints = [
            models.UniqueConstraint(
                fields=["school", "subject", "assessment_type"],
                name="unique_grade_scheme_subject_type",
            )
        ]

    def __str__(self):
        return (
            f"{self.subject} - "
            f"{self.get_assessment_type_display()}"
        )

    def clean(self):
        super().clean()

        if self.subject_id:
            if self.subject.school_id != self.school_id:
                raise ValidationError(
                    "المادة يجب أن تكون تابعة لنفس المدرسة."
                )


class AcademicScheme(SchoolOwnedModel):
    """
    A reusable academic configuration for a group of classrooms.

    A scheme defines:
    - which classrooms use it
    - which subjects those classrooms study
    - how assessments are weighted
    """

    name = models.CharField(
        max_length=150,
        verbose_name="اسم النظام",
    )

    description = models.TextField(
        blank=True,
        verbose_name="الوصف",
    )

    classrooms = models.ManyToManyField(
        Classroom,
        blank=True,
        related_name="academic_schemes",
        verbose_name="الفصول",
    )

    subjects = models.ManyToManyField(
        Subject,
        blank=True,
        related_name="academic_schemes",
        verbose_name="المواد",
    )

    class Meta:
        verbose_name = "نظام أكاديمي"
        verbose_name_plural = "الأنظمة الأكاديمية"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        if not self.school_id:
            return

        # Check that selected classrooms belong to this school.
        if self.pk:
            invalid_classrooms = self.classrooms.exclude(
                school=self.school
            )

            if invalid_classrooms.exists():
                raise ValidationError(
                    "كل الفصول يجب أن تنتمي إلى نفس المدرسة."
                )

            # A classroom can belong to only ONE academic scheme.
            overlapping_classrooms = (
                self.classrooms
                .filter(
                    academic_schemes__school=self.school
                )
                .exclude(
                    academic_schemes=self
                )
                .distinct()
            )

            if overlapping_classrooms.exists():
                classroom_names = ", ".join(
                    overlapping_classrooms.values_list(
                        "name",
                        flat=True
                    )
                )

                raise ValidationError(
                    "الفصول التالية مرتبطة بالفعل بنظام أكاديمي آخر: "
                    + classroom_names
                    + ". لا يمكن للفصل أن ينتمي إلى أكثر من نظام أكاديمي."
                )

            # Check that selected subjects belong to this school.
            invalid_subjects = self.subjects.exclude(
                school=self.school
            )

            if invalid_subjects.exists():
                raise ValidationError(
                    "كل المواد يجب أن تنتمي إلى نفس المدرسة."
                )

class AcademicSchemeRule(SchoolOwnedModel):
    """
    Defines one assessment component inside an academic scheme.

    Example:

    Scheme: Primary Grades
    Type: Exam
    Number of assessments: 2
    Weight: 60%
    """

    class AssessmentType(models.TextChoices):
        EXAM = "exam", "اختبار"
        PROJECT = "project", "مشروع"

    scheme = models.ForeignKey(
        AcademicScheme,
        on_delete=models.CASCADE,
        related_name="rules",
        verbose_name="النظام الأكاديمي",
    )

    assessment_type = models.CharField(
        max_length=20,
        choices=AssessmentType.choices,
        verbose_name="نوع التقييم",
    )

    max_count = models.PositiveIntegerField(
        verbose_name="عدد التقييمات",
    )

    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name="الوزن",
    )

    class Meta:
        verbose_name = "قاعدة درجات"
        verbose_name_plural = "قواعد الدرجات"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "scheme",
                    "assessment_type",
                ],
                name="unique_scheme_rule_type",
            ),
        ]

        ordering = [
            "scheme",
            "assessment_type",
        ]

    def __str__(self):
        return (
            f"{self.scheme.name} - "
            f"{self.get_assessment_type_display()}"
        )

    def clean(self):
        super().clean()

        if self.scheme_id:
            if self.scheme.school_id != self.school_id:
                raise ValidationError(
                    "النظام الأكاديمي يجب أن ينتمي إلى نفس المدرسة."
                )

            # Prevent the grading rules from exceeding 100%.
            existing_rules = AcademicSchemeRule.objects.filter(
                school=self.school,
                scheme=self.scheme,
            )

            if self.pk:
                existing_rules = existing_rules.exclude(
                    pk=self.pk
                )

            existing_total = (
                existing_rules.aggregate(
                    total=Sum("weight")
                )["total"]
                or Decimal("0")
            )

            new_total = existing_total + (
                self.weight or Decimal("0")
            )

            if new_total > Decimal("100"):
                raise ValidationError(
                    f"مجموع أوزان قواعد الدرجات لا يمكن أن يتجاوز 100%. "
                    f"المجموع الحالي سيكون {new_total}%."
                )
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)




class ClassroomSubject(SchoolOwnedModel):
    """
    Defines which subjects are actually taught in a classroom.
    """

    classroom = models.ForeignKey(
        Classroom,
        on_delete=models.CASCADE,
        related_name="classroom_subjects",
        verbose_name="الفصل",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="classroom_subjects",
        verbose_name="المادة",
    )

    class Meta:
        verbose_name = "مادة الفصل"
        verbose_name_plural = "مواد الفصول"
        constraints = [
            models.UniqueConstraint(
                fields=["school", "classroom", "subject"],
                name="unique_classroom_subject",
            )
        ]
        ordering = ["classroom", "subject"]

    def __str__(self):
        return f"{self.classroom} - {self.subject}"

    def clean(self):
        super().clean()

        if self.classroom_id and self.classroom.school_id != self.school_id:
            raise ValidationError(
                "الفصل يجب أن يكون تابعًا لنفس المدرسة."
            )

        if self.subject_id and self.subject.school_id != self.school_id:
            raise ValidationError(
                "المادة يجب أن تكون تابعة لنفس المدرسة."
            )

