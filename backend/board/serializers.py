# board/serializers.py (예시)
from rest_framework import serializers
from .models import Post, Comment

class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "updated_at", "post", "author_username"]
        read_only_fields = ["author", "created_at", "updated_at"]

    def get_author_username(self, obj):
        try:
            if obj.author and not obj.author.is_active:
                return "탈퇴회원"
            return obj.author.username if obj.author else "익명"
        except Exception:
            return "익명"

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

class PostSerializer(serializers.ModelSerializer):
    author_display = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Post
        fields = ["id", "user", "title", "content", "created_at", "updated_at", "comments", "author_display", "views", "category"]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_author_display(self, obj):
        try:
            if obj.user and not obj.user.is_active:
                return "탈퇴회원"
            return obj.user.username if obj.user else "익명"
        except Exception:
            return "익명"

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
