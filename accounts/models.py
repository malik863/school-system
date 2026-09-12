



from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SCHOOL_MANAGER = "school_manager", "مدير المدرسة"
        TEACHER = "teacher", "معلم"
        STUDENT = "student", "طالب"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.TEACHER,
        verbose_name="الدور",
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
        verbose_name="المدرسة",
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
    )

    email_verified = models.BooleanField(
        default=False,
        verbose_name="البريد الإلكتروني موثق",
    )

    class Meta:
        verbose_name = "مستخدم"
        verbose_name_plural = "المستخدمون"

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_school_manager(self):
        return self.role == self.Role.SCHOOL_MANAGER

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

