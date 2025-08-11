# backend/board/views_uploads.py
from uuid import uuid4
from datetime import datetime

from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from PIL import Image, UnidentifiedImageError
import cloudinary.uploader  # ✅ Cloudinary 사용

MAX_SIZE_MB = 5
ALLOWED_FORMATS = {"JPEG", "PNG", "GIF", "WEBP"}  # Pillow 포맷 기준
EXT_MAP = {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}


class ImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # 로그인 필요
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        f = request.FILES.get("image")
        if not f:
            return Response({"detail": "image 파일이 필요합니다."}, status=400)

        if f.size > MAX_SIZE_MB * 1024 * 1024:
            return Response({"detail": f"최대 {MAX_SIZE_MB}MB까지 업로드 가능합니다."}, status=400)

        # 이미지 검증
        try:
            img = Image.open(f)
            img.verify()
        except UnidentifiedImageError:
            return Response({"detail": "이미지 파일이 아닙니다."}, status=400)
        finally:
            f.seek(0)

        fmt = (img.format or "").upper()
        if fmt not in ALLOWED_FORMATS:
            return Response({"detail": f"지원하지 않는 포맷입니다: {fmt}"}, status=400)

        # Cloudinary 업로드 (폴더/파일명 규칙)
        now = datetime.now()
        public_id = f"uploads/{now.year:04d}/{now.month:02d}/{uuid4().hex}"

        try:
            result = cloudinary.uploader.upload(
                f,
                folder=None,
                public_id=public_id,
                resource_type="image",
                overwrite=False,
                unique_filename=False,
                use_filename=False,
            )
        except Exception as e:
            return Response({"detail": f"Cloudinary 업로드 실패: {e}"}, status=500)

        url = result.get("secure_url") or result.get("url")
        if not url:
            return Response({"detail": "업로드 URL 생성 실패"}, status=500)

        # public_id도 함께 반환(삭제 연동에 사용)
        return Response({"url": url, "public_id": result.get("public_id")}, status=status.HTTP_201_CREATED)
