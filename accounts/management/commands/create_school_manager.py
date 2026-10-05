from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import User
from accounts.services import send_manager_setup_email
from schools.models import School


class Command(BaseCommand):
    help = "Create a school manager with no password and email a secure setup link."

    def add_arguments(self, parser):
        parser.add_argument("--school", required=True, help="School slug")
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--first-name", default="")
        parser.add_argument("--last-name", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            school = School.objects.get(slug=options["school"])
        except School.DoesNotExist as exc:
            raise CommandError("School slug was not found.") from exc

        username = options["username"].strip()
        email = options["email"].strip().lower()

        if User.objects.filter(username=username).exists():
            raise CommandError("This username already exists.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("This email is already used by another account.")

        user = User(
            username=username,
            email=email,
            first_name=options["first_name"].strip(),
            last_name=options["last_name"].strip(),
            school=school,
            role=User.Role.SCHOOL_MANAGER,
            is_active=True,
            email_verified=False,
        )
        user.set_unusable_password()
        user.full_clean()
        user.save()

        try:
            send_manager_setup_email(user)
        except Exception as exc:
            # Roll back account creation if the onboarding email cannot be sent.
            raise CommandError(f"Manager was not created because email sending failed: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(
            f"Manager '{username}' created for '{school.name}' and setup email sent to {email}."
        ))
