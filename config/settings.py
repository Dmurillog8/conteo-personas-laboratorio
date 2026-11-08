"""
Configuración del proyecto LabCount.

Aplicativo web para el conteo de personas en el laboratorio.
Stack: Django + OpenCV + PostgreSQL (guía G003-S12).
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga de variables de entorno locales (.env no se versiona).
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-labcount-solo-para-desarrollo-cambiar-en-produccion",
)
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost") or ["127.0.0.1"]
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = False
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", False)
    SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", False)
    CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", False)

# ---------------------------------------------------------------------------
# Aplicaciones
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.core",
    "apps.accounts",
    "apps.monitoring",
    "apps.reports",
]

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
                "apps.core.context_processors.app_info",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de datos: PostgreSQL (requisito de la guía)
# Para pruebas aisladas se puede usar DB_ENGINE=sqlite.
# ---------------------------------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "postgresql").strip().lower()

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "conteo_lab"),
            "USER": os.getenv("DB_USER", "conteo_user"),
            "PASSWORD": os.getenv("DB_PASSWORD", "conteo_pass"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            # Fallo rápido: si PostgreSQL está caído, el sistema lo detecta
            # en pocos segundos y sigue operando en modo degradado.
            "OPTIONS": {
                "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "5")),
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 3,
            },
        }
    }

# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "monitoring:dashboard"
LOGOUT_REDIRECT_URL = "core:landing"

# ---------------------------------------------------------------------------
# Internacionalización
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Archivos estáticos y multimedia
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Tamaño máximo de un video cargado: 250 MB.
DATA_UPLOAD_MAX_MEMORY_SIZE = 250 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# ---------------------------------------------------------------------------
# Parámetros del motor de conteo (OpenCV)
# ---------------------------------------------------------------------------
LABCOUNT_DEFAULT_DETECTOR = os.getenv("LABCOUNT_DEFAULT_DETECTOR", "dnn")
# Modelo YOLO (ONNX) para el detector "dnn". Se descarga con scripts/download_models.py
LABCOUNT_DNN_MODEL = os.getenv("LABCOUNT_DNN_MODEL", str(BASE_DIR / "models" / "yolov5n.onnx"))
# Confianza mínima (0-1). Súbala si aparecen falsos positivos; bájela si no detecta.
LABCOUNT_DNN_CONFIDENCE = float(os.getenv("LABCOUNT_DNN_CONFIDENCE", "0.45"))
LABCOUNT_CAMERA_INDEX = int(os.getenv("LABCOUNT_CAMERA_INDEX", "0"))
LABCOUNT_MAX_FRAME_WIDTH = int(os.getenv("LABCOUNT_MAX_FRAME_WIDTH", "960"))
LABCOUNT_STREAM_FPS = max(5, int(os.getenv("LABCOUNT_STREAM_FPS", "16")))
LABCOUNT_DETECT_EVERY = max(1, int(os.getenv("LABCOUNT_DETECT_EVERY", "2")))
LABCOUNT_SAMPLE_SECONDS = max(1, int(os.getenv("LABCOUNT_SAMPLE_SECONDS", "5")))
LABCOUNT_LINE_ORIENTATION = os.getenv("LABCOUNT_LINE_ORIENTATION", "vertical")
LABCOUNT_LINE_POSITION = float(os.getenv("LABCOUNT_LINE_POSITION", "0.50"))
LABCOUNT_MAX_UPLOAD_MB = 250
# Segundos que se intenta reconectar la cámara antes de cerrar la sesión.
LABCOUNT_RECONNECT_SECONDS = int(os.getenv("LABCOUNT_RECONNECT_SECONDS", "30"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "apps.monitoring": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
