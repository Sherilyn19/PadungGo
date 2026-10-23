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

_DEV_ONLY_SECRET_KEY = "dev-insecure-key-change-me"

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
DEBUG = _bool("DJANGO_DEBUG", default=False)

# Explicit test flag, set only by config/test_settings.py. It selects test-friendly
# infrastructure (SQLite, plain static storage) and never relaxes security:
# the secret-key rule and HTTPS settings below depend on DEBUG alone. (An older
# version guessed "is this a test?" from the command line, which could have
# switched off production protections by accident.)
TESTING = _bool("PADUNGGO_TESTING", default=False)

if not DEBUG and SECRET_KEY in ("", _DEV_ONLY_SECRET_KEY):
    raise RuntimeError(
        "DJANGO_SECRET_KEY must be set to a private random value when DJANGO_DEBUG "
        "is off. Generate one and place it in the environment or backend/.env."
    )
if not SECRET_KEY:
    # Local development only (DEBUG is on); production refuses this key above.
    SECRET_KEY = _DEV_ONLY_SECRET_KEY

ALLOWED_HOSTS = _csv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# Render provides the public hostname (e.g. padunggo-api.onrender.com).
_RENDER_HOST = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if _RENDER_HOST and _RENDER_HOST not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_RENDER_HOST)

# --- Database & spatial mode ----------------------------------------------

# PADUNGGO_DB_ENGINE: "postgis" (default) or "sqlite" (lite/dev-without-GDAL).
# Tests always use lite mode so the suite runs without GDAL/GEOS/PostGIS.
_default_engine = "sqlite" if TESTING else "postgis"
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
    "config.health_middleware.HealthCheckMiddleware",
    # Before CSRF, which would otherwise read a huge body first.
    "config.upload_limit_middleware.UploadSizeLimitMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files (Django Admin CSS/JS) under gunicorn.
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
# Only warn about a missing staticfiles/ dir in production builds.
WHITENOISE_AUTOREFRESH = DEBUG or TESTING
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if TESTING
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- GTFS upload limits ----------------------------------------------------
# Compressed size of an uploaded feed (checked from Content-Length up front).
GTFS_UPLOAD_MAX_BYTES = int(os.environ.get("GTFS_UPLOAD_MAX_MB", "50")) * 1024 * 1024
# Total size once unzipped. Guards against "zip bombs": tiny archives that
# expand into gigabytes and would exhaust memory or time.
GTFS_MAX_UNCOMPRESSED_BYTES = (
    int(os.environ.get("GTFS_MAX_UNCOMPRESSED_MB", "500")) * 1024 * 1024
)

# --- DRF -------------------------------------------------------------------

# How many proxies append to X-Forwarded-For, used to find the real visitor for
# rate limits (see transit/api/throttles.py). Render's chain is Cloudflare then
# Render's own proxy, so the visitor is the 2nd entry from the right. Elsewhere
# (local runs) no proxy is trusted. Set DRF_NUM_PROXIES to override, e.g. 0.
TRUSTED_PROXY_HOPS = int(os.environ.get("DRF_NUM_PROXIES") or (2 if _RENDER_HOST else 0))

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_THROTTLE_CLASSES": [
        "transit.api.throttles.GeneralRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": os.environ.get("DRF_ANON_THROTTLE", "120/min"),
        "plan": os.environ.get("DRF_PLAN_THROTTLE", "30/min"),
        "places": os.environ.get("DRF_PLACES_THROTTLE", "40/min"),
        # Each explanation may call a quota-limited AI provider, so keep this low.
        "explain": os.environ.get("DRF_EXPLAIN_THROTTLE", "6/min"),
    },
    "EXCEPTION_HANDLER": "transit.api.errors.exception_handler",
}

# --- CORS ------------------------------------------------------------------

def _origins(name: str, default: str = "") -> list[str]:
    """Origins are scheme://host[:port] only. Tolerate a pasted trailing slash
    (e.g. 'https://app.vercel.app/'), which django-cors-headers rejects and
    which would otherwise stop the server from starting."""
    return [o.rstrip("/") for o in _csv(name, default)]


CORS_ALLOWED_ORIGINS = _origins(
    "FRONTEND_ORIGIN", "http://localhost:5173,http://127.0.0.1:5173"
)
CORS_ALLOW_CREDENTIALS = False

# --- Security headers (effective when DEBUG is off) ------------------------

if not DEBUG:
    # On Render, HTTPS is enforced at the edge and internal health checks use
    # plain HTTP, so render.yaml sets this to False.
    SECURE_SSL_REDIRECT = _bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SECURE_REDIRECT_EXEMPT = [r"^health$", r"^api/v1/health$"]
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Needed for Django Admin login over HTTPS.
    CSRF_TRUSTED_ORIGINS = _origins("DJANGO_CSRF_TRUSTED_ORIGINS")
    if _RENDER_HOST:
        CSRF_TRUSTED_ORIGINS.append(f"https://{_RENDER_HOST}")

    # HSTS (HTTP Strict Transport Security) tells browsers to use only HTTPS
    # for this host, for the given number of seconds. Browsers remember it, so
    # it starts short (300 s = 5 minutes). Once HTTPS has stayed healthy, raise
    # it step by step with DJANGO_SECURE_HSTS_SECONDS (e.g. 1 day, 1 week,
    # 1 year). Set it to 0 to send no HSTS header at all. Django only sends
    # the header on HTTPS responses.
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "300"))
    # Kept off on purpose until their requirements are confirmed:
    # includeSubDomains would also cover every subdomain of this host, and
    # preload asks browsers to hard-code HTTPS-only, which is slow to undo.
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

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

# --- Address labels and place suggestions (Geoapify) -----------------------
# The key stays on the server: browsers call PadungGo, which calls Geoapify.
# Without a key both features fall back gracefully (no provider results).

GEOAPIFY = {
    "API_KEY": os.environ.get("GEOAPIFY_API_KEY", ""),
    # Switchable without a code change, e.g. Geoapify's EU endpoint.
    "BASE_URL": os.environ.get("GEOAPIFY_BASE_URL", "https://api.geoapify.com/v1/geocode").rstrip("/"),
    # The free plan allows 3,000 credits/day (1 per request); stay below it.
    "DAILY_REQUEST_LIMIT": int(os.environ.get("GEOAPIFY_DAILY_LIMIT", "2500")),
    # Share of the daily limit suggestions may use, reserving the rest for
    # address labels after "My location" or a map pin.
    "SUGGEST_SHARE": float(os.environ.get("GEOAPIFY_SUGGEST_SHARE", "0.8")),
    "TIMEOUT_SECONDS": float(os.environ.get("GEOAPIFY_TIMEOUT_SECONDS", "4")),
    # Suggestions are limited to this lon/lat rectangle (Metro Cebu and nearby).
    "SEARCH_RECT": os.environ.get("GEOAPIFY_SEARCH_RECT", "123.70,10.15,124.10,10.50"),
    # A reverse result farther than this from the point is not shown as its address.
    "MAX_ADDRESS_DISTANCE_M": int(os.environ.get("GEOAPIFY_MAX_ADDRESS_DISTANCE_M", "100")),
}

# --- AI trip explanation (any OpenAI-compatible, open-weight model host) ---
# The key stays on the server: browsers call PadungGo, which calls the provider.
# Without all three of BASE_URL, API_KEY and MODEL the feature reports
# "unavailable" and the journey planner is unaffected.

AI = {
    "BASE_URL": os.environ.get("AI_BASE_URL", "").strip().rstrip("/"),
    "API_KEY": os.environ.get("AI_API_KEY", "").strip(),
    "MODEL": os.environ.get("AI_MODEL", "").strip(),
    "TIMEOUT_SECONDS": float(os.environ.get("AI_TIMEOUT_SECONDS", "10")),
    # Reasoning models spend tokens thinking before they answer, so leave room.
    "MAX_OUTPUT_TOKENS": int(os.environ.get("AI_MAX_OUTPUT_TOKENS", "1200")),
    # "low" keeps answers fast on reasoning models; blank omits the parameter.
    "REASONING_EFFORT": os.environ.get("AI_REASONING_EFFORT", "low").strip(),
    # Groq's free plan allows 1,000 requests a day for the chosen model.
    "DAILY_REQUEST_LIMIT": int(os.environ.get("AI_DAILY_REQUEST_LIMIT", "800")),
    "CACHE_SECONDS": int(os.environ.get("AI_CACHE_SECONDS", str(24 * 60 * 60))),
}
