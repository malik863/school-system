
# core/managers.py
from django.db import models
from .context import get_current_tenant


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        """Allows explicit manual filtering by a specific tenant."""
        return self.filter(school=tenant)


class TenantManager(models.Manager):
    """
    Custom manager that automatically filters all queries 
    by the active tenant context set in request memory.
    """
    def get_queryset(self):
        queryset = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        
        # If a tenant is locked into the request, auto-filter every SELECT query
        if tenant is not None:
            return queryset.filter(school=tenant)
            
        return queryset