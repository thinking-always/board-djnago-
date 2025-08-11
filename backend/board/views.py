# backend/board/views.py
import re
import urllib.parse

from rest_framework import viewsets, permissions
from rest_framework.response import Response
from django.core.cache import cache
from django.db.models import F
import cloudinary.uploader  # ✅ 삭제에 사용

from .models import Post, Comment
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer, CommentSerializer


def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "0.0.0.0")


# --- Cloudinary public_id 추출 유틸 ---
_CLOUDINARY_HOST_RE = re.compile(r'^https?://res\.cloudinary\.com/', re.IGNORECASE)

def _public_id_from_cloudinary_url(url: str):
    """
    예) https://res.cloudinary.com/<cloud>/image/upload/v1754897045/uploads/2025/08/uuid.png
        또는 .../image/upload/f_auto,q_auto/v1234/uploads/2025/08/uuid.png
    -> public_id: uploads/2025/08/uuid
    """
    if not url or not _CLOUDINARY_HOST_RE.search(url):
        return None
    try:
        m = re.search(r'/upload/([^?"]+)', url)
        if not m:
            return None
        after_upload = m.group(1)  # 'v123/...', 또는 'f_auto,q_auto/v123/...'
        parts = after_upload.split('/')
        v_idx = next((i for i, p in enumerate(parts) if p.startswith('v') and p[1:].isdigit()), None)
        if v_idx is None:
            return None
        path_parts = parts[v_idx + 1:]          # ['uploads','2025','08','uuid.png']
        path = '/'.join(path_parts)
        path = path.split('?')[0]               # 쿼리 제거
        path = urllib.parse.unquote(path)       # 디코딩
        if '.' in path:
            path = path.rsplit('.', 1)[0]       # 확장자 제거
        return path or None
    except Exception:
        return None


def _extract_public_ids_from_html(html: str):
    """
    1) data-public-id="..." 속성 우선 사용
    2) 없으면 Cloudinary URL에서 public_id 파싱
    """
    ids = set()
    if not html:
        return []

    for m in re.finditer(r'data-public-id=["\']([^"\']+)["\']', html, flags=re.IGNORECASE):
        ids.add(m.group(1))

    for m in re.finditer(r'src=["\'](https?://res\.cloudinary\.com/[^"\']+)["\']', html, flags=re.IGNORECASE):
        url = m.group(1)
        pid = _public_id_from_cloudinary_url(url)
        if pid:
            ids.add(pid)

    return list(ids)


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        cat = self.request.query_params.get("category")
        if cat in dict(Post.Category.choices):
            qs = qs.filter(category=cat)
        return qs

    def perform_create(self, serializer):
        cat = self.request.data.get("category") or Post.Category.BASIC
        if cat not in dict(Post.Category.choices):
            cat = Post.Category.BASIC
        serializer.save(user=self.request.user, category=cat)

    def retrieve(self, request, *args, **kwargs):
        post = self.get_object()
        ip = _get_client_ip(request)
        key = f"viewed:{post.id}:{ip}"
        if cache.add(key, True, timeout=5):
            Post.objects.filter(pk=post.pk).update(views=F("views") + 1)
            post.refresh_from_db(fields=["views"])
        serializer = self.get_serializer(post)
        return Response(serializer.data)

    # ✅ 게시글 삭제 시 Cloudinary 이미지도 함께 삭제
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        public_ids = _extract_public_ids_from_html(instance.content or "")

        # 먼저 게시글 삭제(권한/검증 우선)
        response = super().destroy(request, *args, **kwargs)

        # 이미지 정리(실패해도 게시글 삭제는 유지)
        for pid in set(public_ids):
            try:
                cloudinary.uploader.destroy(pid, invalidate=True, resource_type="image")
            except Exception:
                # 운영에선 proper 로깅 권장
                print(f"[Cloudinary] 삭제 실패 public_id={pid}")

        return response


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all().order_by("-created_at")
    serializer_class = CommentSerializer
    permission_classes = [IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        post_id = self.request.query_params.get("post")
        if post_id:
            qs = qs.filter(post_id=post_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
