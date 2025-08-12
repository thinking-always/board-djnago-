# accounts/views.py
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

# 선택 모델(없으면 주석처리 가능)
try:
    from .models import UserConsent
except Exception:
    UserConsent = None

User = get_user_model()


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
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip()
        p1 = data.get("password1") or data.get("password") or ""
        p2 = data.get("password2") or data.get("passwordConfirm") or data.get("password_confirmation") or ""

        agree_terms = _to_bool(data.get("agree_terms") or data.get("agree"))
        agree_privacy = _to_bool(data.get("agree_privacy") or data.get("agree"))
        agree_marketing = _to_bool(data.get("agree_marketing") or data.get("marketing_opt_in"))

        errors = {}

        if not username:
            errors.setdefault("username", []).append("아이디는 필수입니다.")
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
# 아이디 찾기
# -----------------------
class UsernameLookupView(APIView):
    """
    body: { email, password }
    resp: 200 {"usernames": [...]} 또는 {"detail": "...못 찾음"}
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get("email") or "").strip()
        password = request.data.get("password") or ""
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
                # 개발 단계에서 에러 파악 시 fail_silently=False 권장
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
        username = (request.data.get("username") or "").strip()
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
