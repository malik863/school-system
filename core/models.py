from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from .managers import TenantManager
from .context import get_current_tenant
from django.conf import settings





class SchoolOwnedModel(models.Model):
    """
    Base model for anything that belongs to exactly one school.

    IMPORTANT:
    We intentionally do NOT automatically filter querysets by the current
    request/tenant. School isolation should be explicit in application code.
    """

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        related_name="%(class)s_records",
    )

    class Meta:
        abstract = True
