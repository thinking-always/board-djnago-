# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf.urls.static import static
from urllib.parse import quote

def social_complete(request):
    if not request.user.is_authenticated:
        return redirect("/accounts/login/")

    r = RefreshToken.for_user(request.user)
    access, refresh = str(r.access_token), str(r)

    fe = settings.FRONTEND_BASE_URL.rstrip("/")

    # ✅ 디버그 용으로 쿼리스트링에도 함께 실어 보낸다 (로컬에서만).
    # 해시(#)와 쿼리(?)를 모두 넣어놓으면 프론트가 어느 쪽이든 파싱 가능.
    url = (
        f"{fe}/social-complete"
        f"?access={quote(access)}&refresh={quote(refresh)}"
        f"#access={quote(access)}&refresh={quote(refresh)}"
    )

    print("[SOCIAL_COMPLETE] redirect ->", url[:200], "...")
    resp = redirect(url)

    # (참고) 백엔드 도메인 쿠키는 프론트 도메인에서 못 읽으니, 지금은 안 심어도 됨.
    return resp

urlpatterns = [
    path("admin/", admin.site.urls),

    # 앱 API
    path("api/", include("board.urls")),

    # 로컬(JWT) 로그인/리프레시는 유지
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    # 기존 accounts 하위(회원가입/비번재설정 등) 유지
    path("api/auth/", include("accounts.urls")),

    # ✅ allauth 웹 라우트(소셜 로그인 진입/콜백)
    path("accounts/", include("allauth.urls")),

    # (선택) dj-rest-auth 엔드포인트 계속 노출해도 무방
    path("dj-rest-auth/", include("dj_rest_auth.urls")),
    path("dj-rest-auth/registration/", include("dj_rest_auth.registration.urls")),

    # ✅ 소셜 완료 → JWT 발급 → 프론트로 리다이렉트
    path("social/complete/", social_complete, name="social_complete"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
