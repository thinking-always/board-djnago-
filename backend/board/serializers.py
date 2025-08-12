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

    # 🔹 author는 ViewSet.perform_create에서 넣으므로 여기선 create 오버라이드 안 함


class PostSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField(read_only=True)
    # 🔹 역참조 comments는 생성 시 입력받지 않도록 읽기전용으로 고정
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Post
        fields = [
            "id", "user", "title", "content",
            "created_at", "updated_at",
            "comments", "author_display",
            "views", "category",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at", "comments", "views"]

    def get_author_display(self, obj):
        try:
            if obj.user and not obj.user.is_active:
                return "탈퇴회원"
            return obj.user.username if obj.user else "익명"
        except Exception:
            return "익명"

    # 🔹 user는 ViewSet.perform_create에서 넣으므로 여기선 create 오버라이드 안 함
