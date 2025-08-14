# config/settings.py
from pathlib import Path
import os
from datetime import timedelta

# --- env / third-party ---
from dotenv import load_dotenv
import dj_database_url
import cloudinary

# === 기본 경로 / .env ===
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def split_env(name: str, default: str = ""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

# === 보안 / 호스트 ===
DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "change-me")
ALLOWED_HOSTS = split_env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

# === CORS / CSRF ===
FRONTEND_ORIGINS = split_env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000" if DEBUG else "",
)
BACKEND_ORIGIN = os.getenv(
    "BACKEND_ORIGIN", "http://localhost:8000" if DEBUG else ""
).strip()

CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CSRF_TRUSTED_ORIGINS = [
    *FRONTEND_ORIGINS, *([BACKEND_ORIGIN] if BACKEND_ORIGIN else [])
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# === 앱 등록 ===
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

# === 미들웨어 ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
] + (
    [] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]  # 로컬 제외, 배포에서만 사용
) + [
    "corsheaders.middleware.CorsMiddleware",     # CORS는 위쪽에 위치
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],  # 필요시 템플릿 폴더 추가
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

# === 데이터베이스 ===
# 기본(로컬): SQLite
DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

# 배포: DATABASE_URL 있으면 Postgres로 전환
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    # 일부 제공자는 postgres:// 를 제공 → psycopg가 요구하는 postgresql://로 치환
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,   # 커넥션 재사용
        ssl_require=True    # SSL 이슈 시 False로 조정 (제공자 문서 확인)
    )

# === 비밀번호 정책 ===
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# === 국제화/시간대 ===
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Australia/Brisbane"
USE_I18N = True
USE_TZ = True

# === 정적/미디어 파일 ===
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

if DEBUG:
    # 로컬 개발: 기본 스토리지
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    # 배포: Whitenoise로 압축/해시된 정적 파일 서빙
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === DRF / JWT ===
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

# === 이메일 ===
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@creeps.local")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# === Cloudinary ===
# CLOUDINARY_URL 하나로 주면 그걸 우선 사용, 아니면 개별 키로 구성
if os.getenv("CLOUDINARY_URL"):
    cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"), secure=True)
else:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

# === 배포 보안 옵션(HTTPS) ===
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True  # 플랫폼이 HTTPS라면 권장
