from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_manager_setup_email(user, request=None):
    """Send a one-time password-setup link to a school manager."""
    if not user.email:
        raise ValueError("Manager must have an email address.")

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse(
        "accounts:password_reset_confirm",
        kwargs={"uidb64": uid, "token": token},
    )

    if request is not None:
        setup_url = request.build_absolute_uri(path)
    else:
        site_url = getattr(settings, "SITE_URL", "").rstrip("/")
        if not site_url:
            raise ValueError("SITE_URL must be configured when no request is supplied.")
        setup_url = f"{site_url}{path}"

    school_name = user.school.name if user.school else "مدرستك"
    name = user.get_full_name() or user.username

    subject = "إعداد كلمة المرور لحساب مدرستك"
    message = f"""مرحباً {name}،

تم إنشاء حساب إدارة {school_name} على منصة مدرستي.

اسم المستخدم: {user.username}

لإنشاء كلمة المرور الخاصة بك، افتح الرابط التالي:
{setup_url}

لأسباب أمنية، لا تشارك هذا الرابط مع أي شخص. إذا تم استخدام الرابط أو تغيير كلمة المرور، فلن يمكن استخدام الرابط القديم مرة أخرى.

منصة مدرستي
"""

    return send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
