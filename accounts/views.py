from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user

        if user.is_superuser:
            return reverse_lazy("admin:index")

        if user.is_school_manager:
            return reverse_lazy("manager:dashboard")

        if user.is_teacher:
            return reverse_lazy("teacher:dashboard")

        if user.is_student:
            return reverse_lazy("core:student_dashboard")

        return reverse_lazy("accounts:login")


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")
