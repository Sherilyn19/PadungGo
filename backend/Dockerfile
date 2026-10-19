# PadungGo backend image (Render). Includes GDAL/GEOS/PROJ for GeoDjango.
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
# used just so settings can import. Real values come from Render environment variables.

RUN PADUNGGO_DB_ENGINE=postgis \
    DATABASE_URL=postgresql://build:build@localhost:5432/build \
    DJANGO_SECRET_KEY=build-only-not-secret \
    DJANGO_DEBUG=False \
    python manage.py collectstatic --noinput

RUN sed -i 's/\r$//' docker-entrypoint.sh && chmod +x docker-entrypoint.sh \
 && useradd --create-home appuser
USER appuser

# Render injects PORT (default 10000); falls back to 8000 locally.
EXPOSE 8000
CMD ["./docker-entrypoint.sh"]
