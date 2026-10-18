"""
Django settings for the PadungGo backend.

Environment-driven; secrets are never hard-coded. See backend/.env.example.

Two run modes are supported so development can proceed without a local PostGIS:

* Full mode (default when DATABASE_URL points at PostGIS): enables
  django.contrib.gis and the PostGIS backend. Requires GDAL + GEOS system libs.
* Lite mode (PADUNGGO_DB_ENGINE=sqlite, or no PostGIS available): uses SQLite,
  omits GeoDjango. Lets the pure-Python planner and API serializers be exercised
  without GDAL/GEOS/PostGIS installed.

The deterministic journey planner (transit/planner/) is pure Python and never
imports django.contrib.gis, so its unit tests run in either mode.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load backend/.env if present (does not override real environment variables).
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str, default: str = "") -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- Core security ---------------------------------------------------------

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = _bool("DJANGO_DEBUG", default=False)

# Detect test runs so the suite does not require production secrets.
_RUNNING_TESTS = bool(os.environ.get("PYTEST_VERSION")) or "PYTEST_CURRENT_TEST" in os.environ \
    or any("pytest" in a or a == "test" for a in sys.argv)

if not SECRET_KEY:
    if DEBUG or _RUNNING_TESTS:
        # Development/test-only ephemeral key; never used when DEBUG is off.
        SECRET_KEY = "dev-insecure-key-change-me"
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG is off. "
            "Generate one and place it in the environment or backend/.env."
        )

ALLOWED_HOSTS = _csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# --- Database & spatial mode ----------------------------------------------

# PADUNGGO_DB_ENGINE: "postgis" (default) or "sqlite" (lite/dev-without-GDAL).
# Tests always use lite mode so the suite runs without GDAL/GEOS/PostGIS.
_default_engine = "sqlite" if _RUNNING_TESTS else "postgis"
DB_ENGINE = os.environ.get("PADUNGGO_DB_ENGINE", _default_engine).strip().lower()
GIS_ENABLED = DB_ENGINE == "postgis"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "transit",
]

if GIS_ENABLED:
    INSTALLED_APPS.insert(0, "django.contrib.gis")

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if GIS_ENABLED:
    DATABASE_URL = os.environ.get("DATABASE_URL")
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is required in PostGIS mode. Set it to your Supabase "
            "PostGIS connection string, or set PADUNGGO_DB_ENGINE=sqlite for "
            "local development without PostGIS."
        )
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            engine="django.contrib.gis.db.backends.postgis",
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": os.environ.get(
                "PADUNGGO_SQLITE_PATH", str(BASE_DIR / "dev.sqlite3")
            ),
        }
    }

# --- Auth / i18n -----------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "Asia/Manila")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- DRF -------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DRF_ANON_THROTTLE", "120/min"),
        "plan": os.environ.get("DRF_PLAN_THROTTLE", "30/min"),
    },
    "EXCEPTION_HANDLER": "transit.api.errors.exception_handler",
}

# --- CORS ------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = _csv(
    "FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ALLOW_CREDENTIALS = False

# --- Security headers (effective when DEBUG is off) ------------------------

if not DEBUG and not _RUNNING_TESTS:
    SECURE_SSL_REDIRECT = _bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = _csv("DJANGO_CSRF_TRUSTED_ORIGINS")

# --- Planner configuration -------------------------------------------------
# Honest-data gating. By default only `verified` records feed trusted journeys.
# Operators may widen the gate for demos with real-but-historic GTFS data; the
# API/UI must then surface a clear "not field-verified" warning.

PLANNER = {
    # Statuses eligible for trusted journey search. "documented" and "candidate"
    # are added only when explicitly enabled below.
    "ALLOW_DOCUMENTED": _bool("PLANNER_ALLOW_DOCUMENTED", default=False),
    # Max straight-line metres from an endpoint to an eligible stop (candidate
    # filter only; NOT a verified walkable route). Documented in docs.
    "STOP_SEARCH_RADIUS_M": int(os.environ.get("PLANNER_STOP_RADIUS_M", "500")),
    # Walking speed used only to qualify approximate straight-line estimates.
    "WALK_SPEED_MPS": float(os.environ.get("PLANNER_WALK_SPEED_MPS", "1.3")),
}
