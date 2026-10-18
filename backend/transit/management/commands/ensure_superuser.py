"""Create or reset the admin account from environment variables.

Used at container start because the Render free plan has no shell. Reads
DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL. Does nothing when they are not
set. If the user exists, its password is reset and it is made an active
superuser, so a forgotten password can be replaced. Remove the variables after
logging in so the password is not left in the environment.
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the superuser from DJANGO_SUPERUSER_* environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        if not username or not password:
            self.stdout.write("ensure_superuser: variables not set; skipping.")
            return

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        created = user is None
        if created:
            user = User(username=username)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            # Never print the password itself.
            self.stderr.write("ensure_superuser: password rejected: " + " ".join(exc.messages))
            return

        user.email = email or user.email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()
        self.stdout.write(
            f"ensure_superuser: {'created' if created else 'reset password for'} '{username}'."
        )
