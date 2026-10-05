from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
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


class UserPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        # A successful setup/reset proves control of the email inbox.
        if self.user and not self.user.email_verified:
            self.user.email_verified = True
            self.user.save(update_fields=["email_verified"])
        return response


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
