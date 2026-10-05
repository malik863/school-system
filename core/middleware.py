
# core/middleware.py
from .context import set_current_tenant

class TenantMiddleware:
    """
    Middleware that attaches the active school context to the current thread/task
    for every incoming request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = None

        # Extract tenant from authenticated user account
        if request.user.is_authenticated and hasattr(request.user, 'school'):
            tenant = request.user.school

        # Attach tenant to request object and lock context memory
        request.tenant = tenant
        set_current_tenant(tenant)

        try:
            response = self.get_response(request)
        finally:
            # Always clear context on request completion or exception
            set_current_tenant(None)

        return response