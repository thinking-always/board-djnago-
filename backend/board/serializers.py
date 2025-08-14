from rest_framework import serializers
from .models import Post, Comment

class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "updated_at", "post", "author_username"]
        read_only_fields = ["id", "author", "created_at", "updated_at"]

    def get_author_username(self, obj):
        try:
            if obj.author and not obj.author.is_active:
                return "탈퇴회원"
            return obj.author.username if obj.author else "익명"
        except Exception:
            return "익명"


class PostSerializer(serializers.ModelSerializer):
    # 👇 프론트가 기대하는 필드 추가
    author = serializers.SerializerMethodField(read_only=True)
    date = serializers.SerializerMethodField(read_only=True)

    # (기존 유지) 상세 화면 등에서 쓸 수 있는 표시용
    author_display = serializers.SerializerMethodField(read_only=True)

    # 역참조 댓글은 읽기전용
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id",
            "user",             # 내부 식별용(읽기전용)
            "title",
            "content",
            "category",
            "views",
            "created_at",
            "updated_at",

            # ✅ 프론트가 쓰는 필드
            "author",
            "date",

            # 보조 필드
            "author_display",
            "comments",
        ]
        read_only_fields = [
            "id", "user", "created_at", "updated_at", "views", "comments",
            "author", "date", "author_display",
        ]

    def get_author(self, obj):
        # 프론트 목록에서 쓰는 author
        try:
            if obj.user and not obj.user.is_active:
                return "탈퇴회원"
            return obj.user.username if obj.user else "익명"
        except Exception:
            return "익명"

    def get_author_display(self, obj):
        # (기존 로직 유지)
        try:
            if obj.user and not obj.user.is_active:
                return "탈퇴회원"
            return obj.user.username if obj.user else "익명"
        except Exception:
            return "익명"

    def get_date(self, obj):
        # 프론트 목록에서 쓰는 date (YYYY-MM-DD)
        # 필요하면 포맷 바꿔도 됨
        return obj.created_at.strftime("%Y-%m-%d")
