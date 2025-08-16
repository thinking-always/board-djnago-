from django.db import models
from django.contrib.auth.models import User


class Post(models.Model):
    class Category(models.TextChoices):
        BASIC = "basic", "워홀 기본 정보"
        JOB_HOUSING = "jobs_housing", "일자리 & 숙소"
        GUIDE = "guide", "가이드"
        TRAVEL = "travel", "워홀 후기 & 여행"
        QNA = "qna", "q&a"

    title = models.CharField(max_length=50)  # (이전 요청대로 50자로 늘려둠)
    content = models.TextField()
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.BASIC,
        db_index=True,
    )

    # ✅ 운영자만 설정 가능한 상단고정(공지)
    is_pinned = models.BooleanField(default=False, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.author.username} - {self.content[:20]}"
