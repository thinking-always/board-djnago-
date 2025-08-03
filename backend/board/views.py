from django.shortcuts import render
from .models import Post
from .permissions import IsAuthorOrReadOnly
from .serializers import PostSerializer
from rest_framework import viewsets, permissions


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by("-created_at")
    serializer_class = PostSerializer
    permission_classes = [IsAuthorOrReadOnly, permissions.IsAuthenticatedOrReadOnly]
    
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
        

    