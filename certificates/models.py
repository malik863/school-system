from django.db import models
from schools.models import SchoolOwnedModel


class CertificateTemplate(SchoolOwnedModel):
    name = models.CharField(max_length=200)

    background = models.ImageField(
        upload_to="certificate_templates/"
    )

    width = models.PositiveIntegerField(default=2480)
    height = models.PositiveIntegerField(default=3508)

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
        ("attendance", "Attendance"),
        ("date", "Date"),
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

    font_name = models.CharField(
        max_length=100,
        default="Arial",
    )

    is_bold = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.template.name} - {self.get_field_type_display()}"