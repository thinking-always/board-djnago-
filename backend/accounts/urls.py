from django.urls import path
from .views import (
    RegisterView,
    UsernameLookupView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordResetIssueByUsernameEmail,
    DeleteAccountView,
)
from accounts.social_views import GoogleLogin
from .views import ChangeUsernameView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("username-lookup/", UsernameLookupView.as_view(), name="username_lookup"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/issue/", PasswordResetIssueByUsernameEmail.as_view(), name="password_reset_issue"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),

    # ✅ 구글 소셜 로그인
    # 최종 경로: /api/auth/social/google/
    path("social/google/", GoogleLogin.as_view(), name="google_login"),
    path("change-username/", ChangeUsernameView.as_view(), name="change_username"),
]
