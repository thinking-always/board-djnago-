from django.contrib import admin
from .models import Post, Comment

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "category", "is_pinned", "created_at", "views")
    list_filter = ("category", "is_pinned", "created_at")
    search_fields = ("title", "content", "user__username")
    actions = ["make_pinned", "make_unpinned"]

    def make_pinned(self, request, queryset):
        updated = queryset.update(is_pinned=True)
        self.message_user(request, f"{updated}개 글을 공지(상단 고정)로 변경했습니다.")
    make_pinned.short_description = "선택 글을 공지(상단 고정)로 설정"

    def make_unpinned(self, request, queryset):
        updated = queryset.update(is_pinned=False)
        self.message_user(request, f"{updated}개 글의 공지를 해제했습니다.")
    make_unpinned.short_description = "선택 글의 공지 해제"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "author", "created_at")
