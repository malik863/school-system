

from django.db import models
from django.core.exceptions import ValidationError

from core.models import SchoolOwnedModel


class School(models.Model):
    name = models.CharField(
        max_length=255,
        verbose_name="اسم المدرسة",
    )

    slug = models.SlugField(
        max_length=100,
        unique=True,
        verbose_name="الرابط المختصر",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="المدرسة مفعلة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "مدرسة"
        verbose_name_plural = "المدارس"
        ordering = ["name"]

    def __str__(self):
        return self.name


class AcademicYear(SchoolOwnedModel):
    name = models.CharField(
        max_length=50,
        verbose_name="اسم العام الدراسي",
    )

    start_date = models.DateField(
        verbose_name="تاريخ البداية",
    )

    end_date = models.DateField(
        verbose_name="تاريخ النهاية",
    )

    is_current = models.BooleanField(
        default=False,
        verbose_name="العام الحالي",
    )

    class Meta:
        verbose_name = "عام دراسي"
        verbose_name_plural = "الأعوام الدراسية"

        ordering = ["-start_date"]

        constraints = [
            models.UniqueConstraint(
                fields=["school", "name"],
                name="unique_academic_year_per_school",
            ),
        ]

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError(
                "تاريخ نهاية العام الدراسي يجب أن يكون بعد تاريخ البداية."
            )
        if self.pk and self.start_date and self.end_date:
            if self.terms.filter(
                models.Q(start_date__lt=self.start_date) | models.Q(end_date__gt=self.end_date)
            ).exists():
                raise ValidationError(
                    "لا يمكن جعل تواريخ العام تستبعد ترماً محفوظاً داخله."
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.is_current:
            AcademicYear.objects.filter(
                school=self.school,
                is_current=True,
            ).exclude(
                pk=self.pk
            ).update(
                is_current=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Term(SchoolOwnedModel):
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name="terms",
        verbose_name="العام الدراسي",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="اسم الترم",
    )

    start_date = models.DateField(
        verbose_name="تاريخ البداية",
    )

    end_date = models.DateField(
        verbose_name="تاريخ النهاية",
    )

    is_current = models.BooleanField(
        default=False,
        verbose_name="الترم الحالي",
    )

    is_closed = models.BooleanField(
        default=False,
        verbose_name="مغلق",
    )

    class Meta:
        verbose_name = "ترم"
        verbose_name_plural = "الترمات"

        ordering = ["start_date"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "school",
                    "academic_year",
                    "name",
                ],
                name="unique_term_per_year",
            ),
        ]

    def clean(self):
        if self.academic_year_id:
            if self.school_id != self.academic_year.school_id:
                raise ValidationError(
                    "الترم والعام الدراسي يجب أن ينتميا إلى نفس المدرسة."
                )

        if self.end_date <= self.start_date:
            raise ValidationError(
                "تاريخ نهاية الترم يجب أن يكون بعد تاريخ البداية."
            )

        if self.academic_year_id and self.start_date and self.end_date:
            if self.start_date < self.academic_year.start_date or self.end_date > self.academic_year.end_date:
                raise ValidationError(
                    "تواريخ الترم يجب أن تكون داخل فترة العام الدراسي."
                )

    def save(self, *args, **kwargs):
        self.full_clean()

        if self.is_current:
            Term.objects.filter(
                school=self.school,
                is_current=True,
            ).exclude(
                pk=self.pk
            ).update(
                is_current=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.academic_year.name}"





