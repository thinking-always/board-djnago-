# accounts/urls.py
from django.urls import path
from .views import (
    RegisterView,
    UsernameLookupView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    PasswordResetIssueByUsernameEmail,
    DeleteAccountView,
)

# 루트에서 이미 "api/auth/" 프리픽스를 붙여서 include 했음.
# 따라서 여기서는 하위 경로만 선언한다.
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),  # /api/auth/register/
    path("username-lookup/", UsernameLookupView.as_view(), name="username_lookup"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password_reset_request"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password_reset_confirm"),
    path("password-reset/issue/", PasswordResetIssueByUsernameEmail.as_view(), name="password_reset_issue"),
    path("delete-account/", DeleteAccountView.as_view(), name="delete_account"),
]
