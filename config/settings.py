from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path
import dj_database_url

from django.contrib.messages import constants as messages_constants

BASE_DIR = Path(__file__).resolve().parent.parent

# Development defaults. Set real values with environment variables in production.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me-in-production-8f3k2j")

# DEBUG defaults to False (production-safe). Set DEBUG=True in .env for local dev.
DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Render gives us a hostname via this env var — auto-add it
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "tickets",
]

AUTH_USER_MODEL = "tickets.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# In production (Render), DATABASE_URL is set by Aiven and takes priority.
# Locally, the DB_* env vars (or defaults) are used.
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Strip any query string from the URL — mysqlclient doesn't accept
    # ssl-mode/sslmode/ssl_mode as kwargs. We force SSL via OPTIONS below.
    clean_url = DATABASE_URL.split("?")[0]
    DATABASES = {
        "default": dj_database_url.parse(
            clean_url,
            conn_max_age=600,
        )
    }
    DATABASES["default"]["OPTIONS"] = {
        "charset": "utf8mb4",
        "ssl": {"ssl_mode": "REQUIRED"},
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.environ.get("DB_NAME", "helpdesk_db"),
            "USER": os.environ.get("DB_USER", "helpdesk_user"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "StrongPass123!"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Dar_es_Salaam"
USE_I18N = True
USE_TZ = True

# ---------- Static & media files ----------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

MESSAGE_TAGS = {messages_constants.ERROR: "danger"}

# ==========================================
# CSRF trusted origins (needed for HTTPS on Render)
# ==========================================
CSRF_TRUSTED_ORIGINS = []
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")

# ==========================================
# SMS (Meseji) settings
# ==========================================
MESEJI_BASE_URL   = os.environ.get("MESEJI_BASE_URL", "https://meseji.co.tz/api/v1")
MESEJI_TOKEN      = os.environ.get("MESEJI_TOKEN", "")
MESEJI_SENDER_ID  = os.environ.get("MESEJI_SENDER_ID", "MESEJI")

# Toggle SMS on/off (useful for dev)
SMS_ENABLED = os.environ.get("SMS_ENABLED", "true").lower() == "true"

# ==========================================
# Logging (so SMS attempts show in console)
# ==========================================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "tickets": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}