"""Create the admin account from environment variables (safe to run on every start).

Runs at container start because the Render free plan has no shell. It reads
DJANGO_SUPERUSER_USERNAME / _PASSWORD / _EMAIL and does nothing when they are
not set.

* The account does not exist: it is created as an active superuser.
* The account already exists: it is left alone. An ordinary restart or
  redeploy never overwrites a password someone has since changed.
* Deliberate recovery (a forgotten password): also set
  DJANGO_SUPERUSER_RESET_PASSWORD=True, or run the command with
  --reset-password. That resets the password and makes the account an active
  superuser. Remove the variable again once you have logged in.

The password is never printed. Remove the variables after first login so the
password is not left in the environment.
"""
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand

_TRUE_VALUES = {"1", "true", "yes", "on"}


class Command(BaseCommand):
    help = (
        "Create the superuser from DJANGO_SUPERUSER_* environment variables. "
        "Existing accounts are left unchanged unless a reset is explicitly requested."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Reset an existing account's password (deliberate recovery only).",
        )

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        reset_requested = options["reset_password"] or (
            os.environ.get("DJANGO_SUPERUSER_RESET_PASSWORD", "").strip().lower() in _TRUE_VALUES
        )
        if not username or not password:
            self.stdout.write("ensure_superuser: variables not set; skipping.")
            return

        User = get_user_model()
        user = User.objects.filter(username=username).first()
        if user is not None and not reset_requested:
            self.stdout.write(
                f"ensure_superuser: '{username}' already exists; leaving it unchanged. "
                "Set DJANGO_SUPERUSER_RESET_PASSWORD=True for a one-off password reset."
            )
            return

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
