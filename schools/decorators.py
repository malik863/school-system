
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def school_admin_required(view_func):
    """
    Allows only authenticated school managers to access
    the school manager area.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("accounts:login")

        if not request.user.is_school_manager:
            raise PermissionDenied(
                "الحساب الحالي لا يملك الصلاحيات الكافية للوصول إلى هذه الصفحة."
            )

        if not request.user.school:
            raise PermissionDenied(
                "هذا الحساب غير مرتبط بمدرسة."
            )

        if not request.user.school.is_active:
            raise PermissionDenied(
                "المدرسة غير مفعلة."
            )

        return view_func(request, *args, **kwargs)

    return wrapper


def teacher_required(view_func):
    """
    Allows only authenticated teachers to access
    the teacher area.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("accounts:login")

        if not request.user.is_teacher:
            raise PermissionDenied(
                "الحساب الحالي لا يملك صلاحية المعلم."
            )

        if not request.user.school:
            raise PermissionDenied(
                "هذا الحساب غير مرتبط بمدرسة."
            )

        if not request.user.school.is_active:
            raise PermissionDenied(
                "المدرسة غير مفعلة."
            )

        return view_func(request, *args, **kwargs)

    return wrapper