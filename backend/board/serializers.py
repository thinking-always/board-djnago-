from rest_framework import serializers
from .models import Post, Comment



class CommentSerializer(serializers.ModelSerializer):
    author_username = serializers.CharField(source='author.username', read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "author", "content", "created_at", "updated_at", "post", "author_username"]
        read_only_fields = ["author", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["author"] = self.context["request"].user
        return super().create(validated_data)

class PostSerializer(serializers.ModelSerializer):
    author = serializers.CharField(source='user.username', read_only=True)                
    date = serializers.DateTimeField(source='created_at', format='%Y-%m-%d', read_only=True)  
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Post
        fields = ["id", "user", "title", "content", "created_at", "updated_at", "comments", "author", "date", "views"]
        read_only_fields = ["user", "created_at", "updated_at"]

    def create(self, validated_data):
        validated_data["user"] = self.context["request"].user
        return super().create(validated_data)
