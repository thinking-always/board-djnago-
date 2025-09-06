# accounts/social_views.py
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from django.conf import settings

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    # ✅ 클래스 속성으로 콜백 고정 (프론트 콜백과 동일)
    callback_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/auth/google/callback"

    # ✅ 임시 디버그: 실제 값 확인
    def post(self, request, *args, **kwargs):
        print("[DEBUG] callback_url =", self.callback_url)
        return super().post(request, *args, **kwargs)
