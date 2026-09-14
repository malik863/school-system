

from contextvars import ContextVar

# 1. Declare a context variable that defaults to None
_current_tenant = ContextVar('current_tenant', default=None)

def set_current_tenant(tenant):
    """Stores the active School object for the current request."""
    return _current_tenant.set(tenant)

def get_current_tenant():
    """Retrieves the active School object for the current request."""
    return _current_tenant.get()