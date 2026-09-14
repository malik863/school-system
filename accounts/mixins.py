# accounts/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied

class SchoolManagerRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Ensures the user is logged in, is a School Admin/Manager, and isolates school data."""
    
    def test_func(self):
        return (
            self.request.user.is_authenticated 
            and hasattr(self.request.user, 'role') 
            and self.request.user.role == 'SCHOOL_ADMIN'
        )

    def get_queryset(self):
        """Automatically filters querysets by the logged-in manager's school."""
        qs = super().get_queryset()
        if hasattr(self.request.user, 'school') and self.request.user.school:
            return qs.filter(school=self.request.user.school)
        return qs.none()

    def form_valid(self, form):
        """Automatically attaches the logged-in manager's school on object creation."""
        form.instance.school = self.request.user.school
        return super().form_valid(form)