# news/views.py
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from .models import NewsItem
from .serializers import NewsItemListSerializer,NewsItemDetailSerializer
from rest_framework.views import APIView
from rest_framework.response import Response

class NewsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50

class NewsListView(generics.ListAPIView):
    serializer_class = NewsItemListSerializer
    permission_classes = [AllowAny]
    pagination_class = NewsPagination

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        qs = NewsItem.objects.filter(published_at__lte=now).filter(
            Q(expires_at__gte=now) | Q(expires_at__isnull=True)
        )
        # Visibility
        if user.is_authenticated:
            qs = qs.filter(
                Q(is_public=True) | Q(target_user=user)
            )
        else:
            qs = qs.filter(is_public=True)
        # Filters
        params = self.request.query_params
        if category := params.get('category'):
            qs = qs.filter(category=category)
        if priority := params.get('priority'):
            qs = qs.filter(priority=priority)
        if start := params.get('start_date'):
            qs = qs.filter(published_at__date__gte=start)
        if end := params.get('end_date'):
            qs = qs.filter(published_at__date__lte=end)
        if show := params.get('show_read'):
            show_read = show.lower() == 'true'
            if user.is_authenticated:
                if show_read:
                    qs = qs.filter(read_by=user)
                else:
                    qs = qs.exclude(read_by=user)
        # Search
        if term := params.get('search'):
            qs = qs.filter(
                Q(title__icontains=term) |
                Q(content__icontains=term) |
                Q(tags__icontains=term)
            )
        return qs




class NewsDetailView(generics.RetrieveAPIView):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        qs = super().get_queryset().filter(published_at__lte=now).filter(
            expires_at__gte=now) | super().get_queryset().filter(
            published_at__lte=now, expires_at__isnull=True)
        if user.is_authenticated:
            return qs.filter(
                models.Q(is_public=True) | models.Q(target_user=user)
            )
        return qs.filter(is_public=True)


class MarkNewsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            news = NewsItem.objects.get(id=id)
        except NewsItem.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Only allow marking visible items
        now = timezone.now()
        if not news.is_public and news.target_user != request.user:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if news.published_at > now or (news.expires_at and news.expires_at < now):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Mark as read
        news.read_by.add(request.user)
        return Response({'success': True}, status=status.HTTP_200_OK)



class UnreadNewsCountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        # Base queryset of visible items
        qs = NewsItem.objects.filter(published_at__lte=now).filter(
            Q(expires_at__gte=now) | Q(expires_at__isnull=True)
        ).filter(
            Q(is_public=True) | Q(target_user=user)
        )
        # Exclude those already read by user
        unread_count = qs.exclude(read_by=user).count()
        return Response({'count': unread_count}, status=status.HTTP_200_OK)
