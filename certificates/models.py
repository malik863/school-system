from django.db import models
from schools.models import SchoolOwnedModel


class CertificateTemplate(SchoolOwnedModel):
    class Period(models.TextChoices):
        TERM_1 = "term_1", "الفصل الأول"
        TERM_2 = "term_2", "الفصل الثاني"
        ACADEMIC_YEAR = "academic_year", "العام الدراسي"

    name = models.CharField(max_length=200)
    period = models.CharField(
        max_length=20, choices=Period.choices, default=Period.TERM_1,
        verbose_name="فترة الشهادة",
        help_text="تحدد الفترة التي يجب اكتمال درجاتها قبل إصدار الشهادة.",
    )

    background = models.ImageField(
        upload_to="certificate_templates/"
    )

    width = models.PositiveIntegerField(default=2480)
    height = models.PositiveIntegerField(default=3508)

    classroom = models.ForeignKey(
        "academics.Classroom", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="certificate_templates",
        help_text="Optional: limits this design to one classroom and its subjects.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name



class CertificateField(models.Model):
    FIELD_TYPES = [
        ("student_name", "Student Name"),
        ("student_id", "Student ID"),
        ("class_name", "Class"),
        ("academic_year", "Academic Year"),
        ("total", "Total"),
        ("percentage", "Percentage"),
        ("result", "Result"),
        ("attendance", "نسبة الحضور"),
        ("attendance_grade", "درجة الحضور"),
        ("date", "Date"),
        ("period_total", "Period Total"),
        ("period_percentage", "Period Percentage"),
        ("subject_name", "Subject Name"),
        ("subject_total", "Subject Total"),
        ("subject_percentage", "Subject Percentage"),
    ]

    ALIGNMENTS = [
        ("left", "Left"),
        ("center", "Center"),
        ("right", "Right"),
    ]

    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    field_type = models.CharField(
        max_length=50,
        choices=FIELD_TYPES,
    )

    # Optional dynamic academic-result reference. When subject is set, the
    # field is resolved from the central grade calculator instead of storing
    # a student's calculated value in the template.
    subject = models.ForeignKey(
        "academics.Subject", on_delete=models.CASCADE, null=True, blank=True,
        related_name="certificate_fields",
    )
    term = models.ForeignKey(
        "schools.Term", on_delete=models.CASCADE, null=True, blank=True,
        related_name="certificate_fields",
    )
    result_value = models.CharField(
        max_length=20,
        choices=[("score", "Total grade"), ("percentage", "Percentage")],
        blank=True,
    )

    label = models.CharField(
        max_length=100,
        blank=True,
    )
# Position
    x = models.FloatField(default=0)
    y = models.FloatField(default=0)

    # Field size
    width = models.FloatField(default=500)
    height = models.FloatField(default=100)
    # Text styling
    font_size = models.PositiveIntegerField(default=40)

    alignment = models.CharField(
        max_length=10,
        choices=ALIGNMENTS,
        default="center",
    )

    FONT_CHOICES = [
        ("Amiri", "Amiri"),
        ("Cairo", "Cairo"),
        ("Tajawal", "Tajawal"),
        ("NotoArabic", "Noto Sans Arabic"),
    ]

    font_name = models.CharField(
        max_length=100,
        choices=FONT_CHOICES,
        default="Amiri",
    )

    font_color = models.CharField(
        max_length=7,
        default="#000000",
    )

    is_bold = models.BooleanField(default=False)
    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.template.name} - {self.get_field_type_display()}"