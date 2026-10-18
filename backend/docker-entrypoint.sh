#!/bin/sh
# Container start script (Render free plan has no pre-deploy hook or shell).
set -e

# Apply migrations (non-destructive) before serving.
python manage.py migrate --noinput

# Optional admin create/reset without shell access. Set
# DJANGO_SUPERUSER_USERNAME / _EMAIL / _PASSWORD in the Render dashboard, deploy
# once, log in, then remove them. An existing user's password is reset.
python manage.py ensure_superuser || echo "ensure_superuser failed; continuing."

exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers 2 --timeout "${GUNICORN_TIMEOUT:-300}" --access-logfile -
