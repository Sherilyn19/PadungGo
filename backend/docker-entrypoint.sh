#!/bin/sh
# Container start script (Render free plan has no pre-deploy hook or shell).
set -e

# Apply migrations (non-destructive) before serving.
python manage.py migrate --noinput

# Optional one-time admin creation without shell access. Set
# DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD in the Render dashboard, deploy
# once, then remove them. An existing user is left untouched.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput || echo "Superuser not created (it may already exist)."
fi

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 --timeout 60 --access-logfile -
