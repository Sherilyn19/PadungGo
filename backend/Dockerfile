# PadungGo backend image (Fly.io). Includes GDAL/GEOS/PROJ for GeoDjango.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# GeoDjango system libraries (per Django's GeoDjango install docs).
RUN apt-get update \
 && apt-get install -y --no-install-recommends binutils libproj-dev gdal-bin \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# collectstatic does not connect to the DB; build-only placeholder values are
# used just so settings can import. Real values come from Fly secrets.
RUN PADUNGGO_DB_ENGINE=postgis \
    DATABASE_URL=postgresql://build:build@localhost:5432/build \
    DJANGO_SECRET_KEY=build-only-not-secret \
    DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]
