# config/settings.py
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv
import cloudinary

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def split_env(name: str, default: str = ""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

# --- 보안/호스트 ---
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
ALLOWED_HOSTS = split_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# --- CORS/CSRF ---
FRONTEND_ORIGINS = split_env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000" if DEBUG else "",
)
BACKEND_ORIGIN = os.getenv(
    "BACKEND_ORIGIN", "http://localhost:8000" if DEBUG else ""
).strip()

CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CSRF_TRUSTED_ORIGINS = [
    *FRONTEND_ORIGINS,
    *( [BACKEND_ORIGIN] if BACKEND_ORIGIN else [] ),
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "corsheaders",

    "board",
    "accounts",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
] + (
    [] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]   # ← 로컬에선 제외
) + [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if DEBUG:
    # dev에선 기본 스토리지로 서빙(Manifest 필요 없음)
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


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

# --- DB (로컬/초기: SQLite) ---
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

# --- 비번 정책 ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Australia/Brisbane"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
}

EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@creeps.local")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# --- Cloudinary ---
if os.getenv("CLOUDINARY_URL"):
    cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"), secure=True)
else:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )
if DEBUG:
    WHITENOISE_USE_FINDERS = True     # 앱/STATICFILES_DIRS에서 바로 로드
    WHITENOISE_AUTOREFRESH = True 
    