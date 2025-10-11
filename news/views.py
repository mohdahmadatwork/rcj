# news/views.py
from django.utils import timezone
from django.db.models import Q
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from .models import NewsItem
from .serializers import NewsItemListSerializer,NewsItemDetailSerializer, NewsItemAdminSerializer, NewsItemCreateSerializerAdmin, NewsItemDetailSerializer, NewsItemUpdateSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from users.models import CustomUser


def is_admin_user(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and hasattr(user, 'user_type') and user.user_type.lower() == 'admin'


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



class AdminNewsListView(generics.ListAPIView):
    """Admin API for listing all news items"""
    serializer_class = NewsItemAdminSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = NewsPagination

    def get_queryset(self):
        user = self.request.user
        if not is_admin_user(user):
            return NewsItem.objects.none()

        queryset = NewsItem.objects.select_related('target_user').prefetch_related('read_by').order_by('-published_at', '-created_at')

        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(excerpt__icontains=search) |
                Q(author__icontains=search) |
                Q(tags__icontains=search)
            )

        # Category filter
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Priority filter
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter == 'published':
            queryset = queryset.filter(published_at__lte=timezone.now())
        elif status_filter == 'draft':
            queryset = queryset.filter(published_at__isnull=True)
        elif status_filter == 'scheduled':
            queryset = queryset.filter(published_at__gt=timezone.now())

        # Public/Private filter
        visibility = self.request.query_params.get('visibility')
        if visibility == 'public':
            queryset = queryset.filter(is_public=True)
        elif visibility == 'private':
            queryset = queryset.filter(is_public=False)

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'result': serializer.data
        })


class AdminNewsCreateView(generics.CreateAPIView):
    """Admin API for creating news items"""
    serializer_class = NewsItemCreateSerializerAdmin
    permission_classes = [IsAuthenticated]
    queryset = NewsItem.objects.all()

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        news_item = serializer.save()

        return Response({
            'success': True,
            'message': 'News item created successfully',
            'data': serializer.to_representation(news_item)
        }, status=status.HTTP_201_CREATED)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_targeting_options(request):
    """Get available targeting options for news creation"""
    
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    

    
    # Get available customers for targeting
    customers = CustomUser.objects.filter(user_type='customer', is_active=True).values(
        'id', 'username', 'first_name', 'last_name', 'email'
    )[:100]  # Limit to 100 for performance
    
    # Format customer data
    customer_options = []
    for customer in customers:
        full_name = f"{customer['first_name']} {customer['last_name']}".strip()
        customer_options.append({
            'id': customer['id'],
            'username': customer['username'],
            'full_name': full_name or customer['username'],
            'email': customer['email']
        })
    
    return Response({
        'success': True,
        'data': {
            'categories': [
                {'value': 'announcement', 'label': 'Announcement'},
                {'value': 'sale', 'label': 'Sale'},
                {'value': 'promotion', 'label': 'Promotion'},
                {'value': 'update', 'label': 'Update'},
                {'value': 'event', 'label': 'Event'},
                {'value': 'personal', 'label': 'Personal'},
                {'value': 'system', 'label': 'System'},
            ],
            'priorities': [
                {'value': 'high', 'label': 'High'},
                {'value': 'medium', 'label': 'Medium'},
                {'value': 'low', 'label': 'Low'},
            ],
            'target_types': [
                {'value': 'all', 'label': 'All Users'},
                {'value': 'specific_user', 'label': 'Specific User'},
                {'value': 'user_group', 'label': 'User Group'},
                {'value': 'customer_segment', 'label': 'Customer Segment'},
            ],
            'customer_types': [
                {'value': 'vip', 'label': 'VIP Customers'},
                {'value': 'new', 'label': 'New Customers'},
                {'value': 'regular', 'label': 'Regular Customers'},
                {'value': 'inactive', 'label': 'Inactive Customers'},
            ],
            'order_statuses': [
                {'value': 'new', 'label': 'New Orders'},
                {'value': 'confirmed', 'label': 'Confirmed Orders'},
                {'value': 'cad_done', 'label': 'CAD Done'},
                {'value': 'rpt_done', 'label': 'RPT Done'},
                {'value': 'casting', 'label': 'Casting'},
                {'value': 'ready', 'label': 'Ready'},
                {'value': 'delivered', 'label': 'Delivered'},
            ],
            'customers': customer_options
        }
    })


# Add this to views.py

from django.shortcuts import get_object_or_404


class AdminNewsDetailView(generics.RetrieveAPIView):
    """Admin API for viewing news item details"""
    serializer_class = NewsItemDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    queryset = NewsItem.objects.all()

    def get_object(self):
        obj = get_object_or_404(NewsItem, id=self.kwargs.get('id'))
        if not is_admin_user(self.request.user):
            self.permission_denied(self.request, message="Admin access required")
        return obj

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


# Alternative function-based approach
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_detail(request, id):
    """Admin API for getting news item details (function-based alternative)"""
    
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news_item = NewsItem.objects.select_related('target_user').prefetch_related(
            'target_users', 'read_by'
        ).get(id=id)
    except NewsItem.DoesNotExist:
        return Response({'error': 'News item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = NewsItemDetailSerializer(news_item)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)


# Additional endpoint to get news analytics
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_analytics(request, id):
    """Get detailed analytics for a news item"""
    
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news_item = NewsItem.objects.get(id=id)
    except NewsItem.DoesNotExist:
        return Response({'error': 'News item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    from .models import NewsReadTracker
    from django.db.models import Count
    from django.utils import timezone
    from datetime import timedelta
    
    # Get read statistics by day (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_reads = NewsReadTracker.objects.filter(
        news_item=news_item,
        read_at__gte=thirty_days_ago
    ).extra({
        'date': 'date(read_at)'
    }).values('date').annotate(
        reads=Count('id')
    ).order_by('date')
    
    # Get reader demographics
    reader_types = NewsReadTracker.objects.filter(
        news_item=news_item
    ).values('user__user_type').annotate(
        count=Count('id')
    )
    
    # Calculate engagement metrics
    total_reads = news_item.read_by.count()
    total_clicks = news_item.click_count
    
    # Calculate potential reach based on targeting
    potential_reach = 0
    if news_item.target_type == 'all' and news_item.is_public:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        potential_reach = User.objects.filter(user_type='customer', is_active=True).count()
    elif news_item.target_type == 'specific_user':
        potential_reach = 1
    elif news_item.target_type == 'user_group':
        potential_reach = news_item.target_users.count()
    elif news_item.target_type == 'customer_segment':
        # Estimate based on segment type
        potential_reach = 100  # Placeholder - implement actual segment counting
    
    engagement_rate = (total_reads / potential_reach * 100) if potential_reach > 0 else 0
    click_through_rate = (total_clicks / total_reads * 100) if total_reads > 0 else 0
    
    return Response({
        'success': True,
        'data': {
            'news_id': str(news_item.id),
            'title': news_item.title,
            'metrics': {
                'total_reads': total_reads,
                'total_clicks': total_clicks,
                'potential_reach': potential_reach,
                'engagement_rate': round(engagement_rate, 2),
                'click_through_rate': round(click_through_rate, 2)
            },
            'daily_reads': list(daily_reads),
            'reader_demographics': list(reader_types),
            'created_at': news_item.created_at.isoformat(),
            'published_at': news_item.published_at.isoformat() if news_item.published_at else None
        }
    })



# Add this to views.py


class AdminNewsUpdateView(generics.UpdateAPIView):
    """Admin API for updating news items (PUT method with full data)"""
    serializer_class = NewsItemUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    queryset = NewsItem.objects.all()
    http_method_names = ['put']  # Only allow PUT method

    def get_object(self):
        obj = get_object_or_404(NewsItem, id=self.kwargs.get('id'))
        if not is_admin_user(self.request.user):
            self.permission_denied(self.request, message="Admin access required")
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        return Response({
            'success': True,
            'message': 'News item updated successfully',
            'data': serializer.to_representation(updated_instance)
        }, status=status.HTTP_200_OK)


# Endpoint to get current news data for editing
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_edit_data(request, id):
    """Get news data formatted for editing form"""
    
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        news_item = NewsItem.objects.select_related('target_user').prefetch_related('target_users').get(id=id)
    except NewsItem.DoesNotExist:
        return Response({'error': 'News item not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Format data for editing form
    edit_data = {
        'id': str(news_item.id),
        'title': news_item.title,
        'content': news_item.content,
        'excerpt': news_item.excerpt,
        'category': news_item.category,
        'priority': news_item.priority,
        'author': news_item.author,
        'published_at': news_item.published_at.isoformat() if news_item.published_at else None,
        'expires_at': news_item.expires_at.isoformat() if news_item.expires_at else None,
        'image_url': news_item.image_url,
        'is_public': news_item.is_public,
        'target_type': news_item.target_type,
        'target_user_id': news_item.target_user.id if news_item.target_user else None,
        'target_user_ids': list(news_item.target_users.values_list('id', flat=True)),
        'target_customer_type': news_item.target_customer_type,
        'target_order_status': news_item.target_order_status,
        'tags': news_item.tags,
        'action_button': news_item.action_button,
        'related_order_id': news_item.related_order_id,
        
        # Additional info for display
        'created_at': news_item.created_at.isoformat() if news_item.created_at else None,
        'updated_at': news_item.updated_at.isoformat() if news_item.updated_at else None,
        'read_count': news_item.read_by.count(),
        'click_count': news_item.click_count,
        'auto_generated': news_item.auto_generated,
    }
    
    return Response({
        'success': True,
        'data': edit_data
    }, status=status.HTTP_200_OK)