from rest_framework import viewsets, permissions
from .models import Post, Comment
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer, CommentSerializer
from rest_framework.response import Response 
from django.core.cache import cache

def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        
    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
       
        
        ip = _get_client_ip(request)
        key = f"viewed:{post.id}:{ip}"
        if not cache.get(key):
            post.views = (post.views or 0) + 1
            post.save(update_fields=["views"])
            cache.set(key, True, timeout=5)
        
        serializer = self.get_serializer(post)
        return Response(serializer.data)

class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by("-created_at")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly]

    # ⭐ 목록에서 ?post=ID 필터링 지원
    def get_queryset(self):
        qs = super().get_queryset()
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    # ⭐ 생성 시 author 자동 주입 (body로 넘어온 post와 함께 저장)
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
