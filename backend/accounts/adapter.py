from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class MyAccountAdapter(DefaultAccountAdapter):
    # 추가 입력 없이도 가입 열어두기
    def is_open_for_signup(self, request):
        return True

class MySocialAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        프로바이더가 username을 안 줘도 자동으로 만들어 넣는다.
        우선순위: nickname > name > provider uid
        """
        user = super().populate_user(request, sociallogin, data)
        # 이미 세팅됐으면 건너뜀
        if getattr(user, "username", None):
            return user

        # 후보값 뽑기
        cand = (
            data.get("nickname")
            or data.get("name")
            or sociallogin.account.extra_data.get("nickname")
            or sociallogin.account.extra_data.get("name")
            or sociallogin.account.uid
            or "user"
        )

        # allauth가 제공하는 고유 유저네임 생성기로 충돌 없이 생성
        user.username = self.account_adapter.generate_unique_username([str(cand)])
        return user
