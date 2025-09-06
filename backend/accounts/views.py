# accounts/views.py
import re
import unicodedata

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

# 선택 모델(없으면 주석처리 가능)
try:
    from .models import UserConsent
except Exception:
    UserConsent = None

User = get_user_model()

# ✅ 한글(가-힣) 포함 허용, 길이 3~20
USERNAME_RE = re.compile(r"^[a-zA-Z0-9가-힣._-]{3,20}$")

def _norm_username(s: str) -> str:
    """유니코드 NFC 정규화 + 공백 제거"""
    return unicodedata.normalize("NFC", (s or "").strip())

def get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _to_bool(v):
    return str(v).strip().lower() in ("1", "true", "on", "yes")


# -----------------------
# 회원가입
# -----------------------
class RegisterView(APIView):
    """
    간단 회원가입:
    - body: { username, email?, password1, password2, agree_terms, agree_privacy, agree_marketing? }
    - resp: 201 Created
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data

        # 키 유연 처리(프론트가 password/passwordConfirm를 보내도 수용)
        raw_username = data.get("username") or ""
        username = _norm_username(raw_username)
        email = (data.get("email") or "").strip()
        p1 = data.get("password1") or data.get("password") or ""
        p2 = data.get("password2") or data.get("passwordConfirm") or data.get("password_confirmation") or ""

        agree_terms = _to_bool(data.get("agree_terms") or data.get("agree"))
        agree_privacy = _to_bool(data.get("agree_privacy") or data.get("agree"))
        agree_marketing = _to_bool(data.get("agree_marketing") or data.get("marketing_opt_in"))

        errors = {}

        if not username:
            errors.setdefault("username", []).append("아이디는 필수입니다.")
        elif not USERNAME_RE.fullmatch(username):
            errors.setdefault("username", []).append("3~20자, 영문/숫자/한글/._- 만 가능합니다.")
        if not p1:
            errors.setdefault("password1", []).append("비밀번호는 필수입니다.")
        if not p2:
            errors.setdefault("password2", []).append("비밀번호 확인은 필수입니다.")
        if p1 and p2 and p1 != p2:
            errors.setdefault("password2", []).append("비밀번호가 일치하지 않습니다.")
        if not agree_terms:
            errors.setdefault("agree_terms", []).append("이용약관 동의가 필요합니다.")
        if not agree_privacy:
            errors.setdefault("agree_privacy", []).append("개인정보 처리방침 동의가 필요합니다.")
        if username and User.objects.filter(username__iexact=username).exists():
            errors.setdefault("username", []).append("이미 사용 중인 아이디입니다.")

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(p1)
        except ValidationError as e:
            return Response({"errors": {"password1": e.messages}}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email or "", password=p1)

            if UserConsent:
                try:
                    policy_version = getattr(settings, "POLICY_VERSION", "1.0")
                    UserConsent.objects.create(
                        user=user,
                        terms_version=policy_version,
                        privacy_version=policy_version,
                        marketing_agree=agree_marketing,
                        ip=get_client_ip(request),
                    )
                except Exception:
                    # 동의 로그 실패는 회원가입 진행에 영향 없음
                    pass

        return Response({"detail": "회원가입이 완료되었습니다."}, status=status.HTTP_201_CREATED)


# -----------------------
# 아이디 찾기 / 아이디 가용성
# -----------------------
class UsernameLookupView(APIView):
    """
    1) 아이디 가용성 확인
       - GET  /auth/username-lookup/?username=<name>
       - POST /auth/username-lookup/ { "username": "<name>" }
       resp: 200 { "exists": bool, "available": bool }

    2) 아이디 찾기(이메일+비밀번호)
       - POST /auth/username-lookup/ { "email": "...", "password": "..." }
       resp: 200 { "usernames": [...] } 또는 { "detail": "...못 찾음" }
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def get(self, request):
        username = _norm_username(request.query_params.get("username") or "")
        if not username:
            return Response({"detail": "username 파라미터가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        exists = User.objects.filter(username__iexact=username).exists()
        return Response({"exists": bool(exists), "available": not exists}, status=status.HTTP_200_OK)

    def post(self, request):
        data = request.data or {}

        # (A) username 가용성 확인 (POST로도 허용)
        raw_username = data.get("username") or ""
        username = _norm_username(raw_username)
        if username:
            exists = User.objects.filter(username__iexact=username).exists()
            return Response({"exists": bool(exists), "available": not exists}, status=status.HTTP_200_OK)

        # (B) 이메일 + 비밀번호로 아이디 찾기
        email = (data.get("email") or "").strip()
        password = data.get("password") or ""
        if not email or not password:
            return Response({"detail": "이메일과 비밀번호를 입력하세요."}, status=status.HTTP_400_BAD_REQUEST)

        users = User.objects.filter(email__iexact=email)
        matched = [u.username for u in users if u.check_password(password)]

        if not matched:
            return Response(
                {"detail": "확인되었습니다. 입력한 정보와 일치하는 계정을 찾지 못했습니다."},
                status=status.HTTP_200_OK,
            )
        return Response({"usernames": matched}, status=status.HTTP_200_OK)


# -----------------------
# (메일링 방식) 비밀번호 재설정 요청
# -----------------------
class PasswordResetRequestView(APIView):
    """
    body: { email }
    resp: 200 항상 OK(정보 노출 방지)
    - 개발 환경에서는 EMAIL_BACKEND 콘솔/파일 사용 권장
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        ok_msg = {"detail": "비밀번호 재설정 메일을 발송했습니다. 메일함을 확인하세요."}
        if not email:
            return Response(ok_msg, status=status.HTTP_200_OK)

        users = User.objects.filter(email__iexact=email, is_active=True)
        if users.exists():
            token_gen = PasswordResetTokenGenerator()
            frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)

            for u in users:
                uid = urlsafe_base64_encode(force_bytes(u.pk))
                token = token_gen.make_token(u)
                reset_url = f"{frontend_base}/reset-password?uid={uid}&token={token}"

                subject = "[Creeps] 비밀번호 재설정 안내"
                body = (
                    f"{u.username} 님,\n\n"
                    f"아래 링크에서 비밀번호를 재설정하세요:\n{reset_url}\n\n"
                    f"본 메일은 요청하신 경우에만 발송됩니다. 요청하지 않았다면 무시하세요."
                )
                EmailMessage(subject, body, from_email=from_email, to=[email]).send(fail_silently=True)

        return Response(ok_msg, status=status.HTTP_200_OK)


# -----------------------
# (메일 또는 토큰 기반) 비밀번호 재설정 확정
# -----------------------
class PasswordResetConfirmView(APIView):
    """
    body: { uid, token, new_password1, new_password2 }
    resp: 200 {"detail": "..."}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        p1 = request.data.get("new_password1") or ""
        p2 = request.data.get("new_password2") or ""

        if not uid or not token:
            return Response({"detail": "잘못된 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)
        if not p1 or not p2 or p1 != p2:
            return Response({"new_password2": ["비밀번호가 일치하지 않습니다."]}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid_int = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid_int, is_active=True)
        except Exception:
            return Response({"detail": "토큰이 유효하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        token_gen = PasswordResetTokenGenerator()
        if not token_gen.check_token(user, token):
            return Response({"detail": "토큰이 유효하지 않습니다."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(p1, user=user)
        except ValidationError as e:
            return Response({"new_password1": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(p1)
        user.save(update_fields=["password"])
        return Response({"detail": "비밀번호가 변경되었습니다."}, status=status.HTTP_200_OK)


# -----------------------
# (이메일 없이) 아이디+이메일로 토큰 즉시 발급
# -----------------------
class PasswordResetIssueByUsernameEmail(APIView):
    """
    이메일 발송 없이, 아이디+이메일이 맞으면 reset 파라미터(uid, token) 발급
    body: { username, email }
    resp: 200 {"uid": "...", "token": "..."}
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        username = _norm_username(request.data.get("username") or "")
        email = (request.data.get("email") or "").strip()

        if not username or not email:
            return Response({"errors": {"detail": ["아이디와 이메일을 입력하세요."]}}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username__iexact=username, email__iexact=email, is_active=True)
        except User.DoesNotExist:
            # 계정 존재 노출 방지
            return Response({"errors": {"detail": ["정보가 일치하지 않습니다."]}}, status=status.HTTP_400_BAD_REQUEST)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)
        return Response({"uid": uid, "token": token}, status=status.HTTP_200_OK)


# -----------------------
# 회원 탈퇴(소프트 삭제)
# -----------------------
class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        password = request.data.get("password") or ""
        user = request.user

        if not user.check_password(password):
            return Response({"password": ["비밀번호가 올바르지 않습니다."]}, status=status.HTTP_400_BAD_REQUEST)

        # 개인정보 비식별화 + 계정 비활성
        user.email = ""
        if hasattr(user, "first_name"):
            user.first_name = ""
        if hasattr(user, "last_name"):
            user.last_name = ""

        from django.utils import timezone
        ts = timezone.now().strftime("%Y%m%d%H%M%S")
        user.username = f"deleted_{user.pk}_{ts}"
        user.is_active = False
        user.save()

        return Response(status=status.HTTP_204_NO_CONTENT)


# -----------------------
# 아이디(유저네임) 변경
# -----------------------
class ChangeUsernameView(APIView):
    """
    JWT 인증 필요.
    - 소셜 계정: 비밀번호 없이 변경 가능
    - 로컬 계정: 비밀번호 확인 후 변경 (user.has_usable_password() == True 이면 password 필수)
    입력: { "new_username": "...", "password": "..."(옵션) }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        new_username = _norm_username(request.data.get("new_username") or "")
        password = request.data.get("password", "")

        # 1) 입력 검증
        if not new_username:
            return Response({"new_username": ["아이디를 입력해 주세요."]}, status=status.HTTP_400_BAD_REQUEST)
        if not USERNAME_RE.fullmatch(new_username):
            return Response({"new_username": ["3~20자, 영문/숫자/한글/._- 만 가능합니다."]}, status=status.HTTP_400_BAD_REQUEST)

        # 2) 동일 아이디 변경 방지 (정규화 후 비교)
        if new_username.lower() == (unicodedata.normalize("NFC", user.username or "").lower()):
            return Response({"detail": "현재 아이디와 동일합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 3) 중복 체크(대소문자 무시, 정규화된 값으로)
        exists = User.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists()
        if exists:
            return Response({"new_username": ["이미 사용 중인 아이디입니다."]}, status=status.HTTP_400_BAD_REQUEST)

        # 4) 로컬 계정은 비밀번호 확인, 소셜 계정은 생략 가능
        if user.has_usable_password():
            if not password:
                return Response({"password": ["현재 비밀번호를 입력해 주세요."]}, status=status.HTTP_400_BAD_REQUEST)
            if not user.check_password(password):
                return Response({"password": ["비밀번호가 올바르지 않습니다."]}, status=status.HTTP_400_BAD_REQUEST)

        # 5) 변경
        user.username = new_username
        user.save(update_fields=["username"])

        return Response({"username": user.username}, status=status.HTTP_200_OK)
