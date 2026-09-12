from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

def role_required(*allowed_roles):
    """Restricts access to users matching specific roles."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role in allowed_roles or request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapper
    return decorator