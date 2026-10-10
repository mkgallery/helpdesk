from dotenv import load_dotenv
load_dotenv()
import os
from pathlib import Path

from django.contrib.messages import constants as messages_constants

BASE_DIR = Path(__file__).resolve().parent.parent

# Development defaults. Set real values with environment variables in production.
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key-change-me-in-production-8f3k2j")
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

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
TIME_ZONE = "UTC"  # change to your own time zone
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

MESSAGE_TAGS = {messages_constants.ERROR: "danger"}
# ==========================================
# SMS (Meseji) settings
# ==========================================
import os

MESEJI_BASE_URL   = os.environ.get("MESEJI_BASE_URL", "https://meseji.co.tz/api/v1")
MESEJI_TOKEN      = os.environ.get("MESEJI_TOKEN", "zs_e07e2a65e2301a88631c04b872f30c66296678bdde416f7c")
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