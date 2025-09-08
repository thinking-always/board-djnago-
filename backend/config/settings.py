# config/settings.py
from pathlib import Path
import os
from datetime import timedelta

# --- env / third-party ---
from dotenv import load_dotenv
import dj_database_url
import cloudinary
from corsheaders.defaults import default_headers, default_methods

# === 기본 경로 / .env ===
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def split_env(name: str, default: str = "") -> list[str]:
    """쉼표로 구분된 ENV를 리스트로 파싱"""
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]

# === 보안 / 호스트 ===
# 로컬 디폴트는 True로 (개발 편의), 배포에선 ENV로 False 주입
DEBUG = os.getenv("DJANGO_DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret")
ALLOWED_HOSTS = split_env("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")

# === CORS / CSRF ===
# 프론트 기원(로컬 기본 포함)
FRONTEND_ORIGINS = split_env(
    "FRONTEND_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000",
)

# 백엔드 기원(로컬 기본 포함) — CSRF 신뢰 출처에 넣어줌
BACKEND_ORIGINS = split_env(
    "BACKEND_ORIGINS",
    "http://127.0.0.1:8000,http://localhost:8000",
)
# (하위호환) 단일 키 쓰던 프로젝트 대응
_legacy = os.getenv("BACKEND_ORIGIN", "").strip()
if _legacy and _legacy not in BACKEND_ORIGINS:
    BACKEND_ORIGINS.append(_legacy)

CORS_ALLOWED_ORIGINS = FRONTEND_ORIGINS
CSRF_TRUSTED_ORIGINS = [*FRONTEND_ORIGINS, *BACKEND_ORIGINS]

# 프록시/HTTPS 환경에서 원래 스킴 복구
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# === 앱 등록 ===
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    'django.contrib.sites',
    
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.naver',

    "rest_framework",
    'dj_rest_auth',
    'dj_rest_auth.registration',
    "corsheaders",

    "board",
    "accounts",
]

# === 미들웨어 ===
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # ✅ 배포에서만 WhiteNoise 사용 (로컬에선 runserver가 정적 제공)
    *([] if DEBUG else ["whitenoise.middleware.WhiteNoiseMiddleware"]),

    # ✅ CORS는 CommonMiddleware 보다 위에
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    
    "allauth.account.middleware.AccountMiddleware", # 추가(소셜 계정)
    
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

# 배포·외부 DB: DATABASE_URL 있으면 전환
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # 외부 DB SSL 필요 여부: 배포 True / 로컬 False 기본, ENV로 덮기 가능
    DB_SSL_REQUIRE = os.getenv("DB_SSL_REQUIRE", "true" if not DEBUG else "false").lower() == "true"
    DATABASES["default"] = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=600,
        ssl_require=DB_SSL_REQUIRE,
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
    # 로컬: Django 기본 스토리지(collectstatic 불필요)
    STATICFILES_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"
else:
    # 배포: WhiteNoise로 압축/해시
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# === DRF / JWT ===
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # 전역 권한은 ViewSet에서 개별 지정했으니 생략(필요시 추가)
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# === 이메일 ===
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@creeps.local")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")

# === Cloudinary ===
if os.getenv("CLOUDINARY_URL"):
    cloudinary.config(cloudinary_url=os.getenv("CLOUDINARY_URL"), secure=True)
else:
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True,
    )

# === CORS 상세 (로컬 디버깅 완충) ===
# Authorization 헤더 허용
CORS_ALLOW_HEADERS = list(default_headers) + ["authorization"]
CORS_ALLOW_METHODS = list(default_methods)

# 로컬 디버깅 중엔 모두 허용(문제 해결 후 해제해도 됨)
CORS_ALLOW_ALL_ORIGINS = DEBUG

# === 배포 보안 옵션(HTTPS) ===
# if not DEBUG:
#     SECURE_SSL_REDIRECT = True --------------------------------------------배포시
#     SESSION_COOKIE_SECURE = True
#     CSRF_COOKIE_SECURE = True
# else:
#     # 로컬에서 켜져 있으면 CORS가 막히므로 명시적으로 꺼둠
#     SECURE_SSL_REDIRECT = False

if DEBUG:
    SECURE_SSL_REDIRECT = False
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_HSTS_SECONDS = 0

SITE_ID = int(os.getenv("SITE_ID", "1"))
ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

# ------------------------------------------------------------#siteid

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',                  # 기본
    'allauth.account.auth_backends.AuthenticationBackend',        # allauth
]


ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_AUTHENTICATION_METHOD = "username"   # 필요시 "email"로 변경
ACCOUNT_EMAIL_REQUIRED = False

# dj-rest-auth를 JWT 모드로 전환 + 토큰 모델 비활성화
REST_USE_JWT = True
REST_AUTH = {
    "TOKEN_MODEL": None,
}

# allauth 최신 키
ACCOUNT_LOGIN_METHODS = {"username", "email"}  # 둘 다 허용. 한 쪽만이면 {"username"} 또는 {"email"}

REST_USE_JWT = True
REST_AUTH = {
    "TOKEN_MODEL": None,  # authtoken 비활성화
}
# 소셜 로그인 성공 후 이동할 URL (서버 세션 기준)
LOGIN_REDIRECT_URL = "/social/complete/"
SOCIALACCOUNT_LOGIN_ON_GET = True

CORS_ALLOW_CREDENTIALS=True

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https" 

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "secret": os.getenv("GOOGLE_SECRET", ""),
            "key": "",
        }
    },
    "naver": {
        "APP": {
            "client_id": os.getenv("NAVER_CLIENT_ID", ""),
            "secret": os.getenv("NAVER_SECRET", ""),
            "key": "",
        }
    },
    "kakao": {
        "APP": {
            "client_id": os.getenv("KAKAO_CLIENT_ID", ""),
            "secret": os.getenv("KAKAO_SECRET", ""),  # 카카오는 시크릿이 없을 수도 있음
            "key": "",
        }
    },
}
