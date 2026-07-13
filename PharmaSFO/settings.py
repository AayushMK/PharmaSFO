import os
import sys
from pathlib import Path
from datetime import timedelta

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "django-insecure-dev-key-change-me"
)
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() in ("true", "1")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

# Railway injects the service's public hostname; trust it without hand-listing it.
RAILWAY_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN")
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")

# Railway terminates TLS at the edge and forwards the request over plain HTTP.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "ninja_extra",
    "ninja_jwt",
    # Local
    "users",
    "doctors",
    "doctor_employee_relation",
    "tour_plans",
    "daily_coverage",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Serves collected static files in production (must sit right after SecurityMiddleware)
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "PharmaSFO.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "users.context_processors.nav_counts",
            ],
        },
    },
]

WSGI_APPLICATION = "PharmaSFO.wsgi.application"

# Managed hosts (Railway) hand the app a single DATABASE_URL; local Docker Compose
# passes the POSTGRES_* parts via .env.
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# A reference Railway couldn't resolve (wrong service name) arrives as the literal
# "${{...}}" text. Treat it as absent rather than feeding it to the URL parser.
UNRESOLVED_DB_REF = DATABASE_URL.startswith("${{")
if UNRESOLVED_DB_REF:
    DATABASE_URL = ""

ON_RAILWAY = bool(
    os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID")
)
# collectstatic runs inside `docker build`, where Railway's service variables are
# NOT injected into RUN steps — only declared ARGs are. It touches no database, so
# it must never demand DB config, or the guard below would fail every image build.
BUILDING_IMAGE = "collectstatic" in sys.argv

# Without this, a missing DATABASE_URL silently falls through to the localhost
# default below and surfaces as a baffling "connection to localhost refused".
if ON_RAILWAY and not DATABASE_URL and not BUILDING_IMAGE:
    visible = sorted(
        k for k in os.environ
        if k.startswith(("DATABASE", "PG", "POSTGRES", "RAILWAY_ENVIRONMENT"))
    )
    detail = (
        "DATABASE_URL is set, but Railway could not resolve the reference — the "
        "database service name in ${{ServiceName.DATABASE_URL}} does not match any "
        "service in this project."
        if UNRESOLVED_DB_REF else
        "DATABASE_URL is not set on this service. Add it under Variables with the "
        "value ${{Postgres.DATABASE_URL}}, using your database service's exact name."
    )
    raise ImproperlyConfigured(
        f"{detail}\nDjango would otherwise fall back to localhost, where no Postgres "
        f"is running.\nDatabase/Railway variables visible here: {visible or 'NONE'}"
    )

if DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL, conn_max_age=600, conn_health_checks=True
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "pharmasfo"),
            "USER": os.environ.get("POSTGRES_USER", "pharmasfo"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "pharmasfo_dev_password"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        }
    }

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kathmandu"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# Django Ninja JWT
NINJA_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}
