# news/views.py

from django.utils import timezone
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, parsers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import timedelta

from .models import NewsItem, NewsReadTracker
from .serializers import (
    NewsItemListSerializer, NewsItemDetailSerializer, 
    NewsItemAdminSerializer, NewsItemCreateSerializerAdmin, 
    NewsItemUpdateSerializer, NewsItemAdminDetailSerializer
)
from users.models import CustomUser


def is_admin_user(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and hasattr(user, 'user_type') and user.user_type.lower() == 'admin'


class NewsPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50


class NewsListView(generics.ListAPIView):
    """Public API for listing published news items"""
    serializer_class = NewsItemListSerializer
    permission_classes = [AllowAny]
    pagination_class = NewsPagination

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        
        # Base queryset - only published and not expired
        qs = NewsItem.objects.filter(
            published_at__lte=now
        ).filter(
            Q(expires_at__gte=now) | Q(expires_at__isnull=True)
        )

        # Visibility filtering
        if user.is_authenticated:
            # Show public items and items targeted to this user
            qs = qs.filter(
                Q(is_public=True) | 
                Q(target_user=user) |
                Q(target_users=user)
            )
        else:
            # Only public items for anonymous users
            qs = qs.filter(is_public=True)

        # Additional filtering based on targeting
        if user.is_authenticated:
            # Apply customer segment targeting if applicable
            if hasattr(user, 'customer_type'):
                qs = qs.filter(
                    Q(target_type='all') |
                    Q(target_type='specific_user', target_user=user) |
                    Q(target_type='user_group', target_users=user) |
                    Q(target_type='customer_segment', target_customer_type=user.customer_type) |
                    Q(target_type='customer_segment', target_customer_type__isnull=True)
                )

        # Query parameters for filtering
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

        # Search functionality
        if term := params.get('search'):
            qs = qs.filter(
                Q(title__icontains=term) |
                Q(content__icontains=term) |
                Q(excerpt__icontains=term) |
                Q(tags__icontains=term)
            )

        return qs.select_related('target_user').prefetch_related('read_by').order_by('-published_at', '-created_at')


class NewsDetailView(generics.RetrieveAPIView):
    """Public API for viewing individual news items"""
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'id'

    def get_queryset(self):
        user = self.request.user
        now = timezone.now()
        
        # Only published and not expired items
        qs = NewsItem.objects.filter(
            published_at__lte=now
        ).filter(
            Q(expires_at__gte=now) | Q(expires_at__isnull=True)
        )

        # Visibility filtering
        if user.is_authenticated:
            return qs.filter(
                Q(is_public=True) | 
                Q(target_user=user) |
                Q(target_users=user)
            )
        return qs.filter(is_public=True)


class MarkNewsReadView(APIView):
    """API endpoint to mark news items as read"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        try:
            news = NewsItem.objects.get(id=id)
        except NewsItem.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Verify user can access this news item
        now = timezone.now()
        if not news.can_be_viewed_by(request.user):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if not news.is_published():
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Mark as read using the model method
        tracker = news.mark_read_by(request.user)
        
        return Response({
            'success': True,
            'message': 'News marked as read',
            'read_at': tracker.read_at.isoformat() if tracker else None
        }, status=status.HTTP_200_OK)


class UnreadNewsCountView(APIView):
    """API endpoint to get count of unread news items"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()

        # Base queryset of visible items
        qs = NewsItem.objects.filter(
            published_at__lte=now
        ).filter(
            Q(expires_at__gte=now) | Q(expires_at__isnull=True)
        ).filter(
            Q(is_public=True) | 
            Q(target_user=user) |
            Q(target_users=user)
        )

        # Apply targeting filters
        if hasattr(user, 'customer_type'):
            qs = qs.filter(
                Q(target_type='all') |
                Q(target_type='specific_user', target_user=user) |
                Q(target_type='user_group', target_users=user) |
                Q(target_type='customer_segment', target_customer_type=user.customer_type)
            )

        # Exclude those already read by user
        unread_count = qs.exclude(read_by=user).count()
        
        return Response({'count': unread_count}, status=status.HTTP_200_OK)


# ADMIN VIEWS

class AdminNewsListView(generics.ListAPIView):
    """Admin API for listing all news items with comprehensive filtering"""
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
        now = timezone.now()
        if status_filter == 'published':
            queryset = queryset.filter(
                published_at__lte=now
            ).filter(
                Q(expires_at__gte=now) | Q(expires_at__isnull=True)
            )
        elif status_filter == 'draft':
            queryset = queryset.filter(published_at__isnull=True)
        elif status_filter == 'scheduled':
            queryset = queryset.filter(published_at__gt=now)
        elif status_filter == 'expired':
            queryset = queryset.filter(expires_at__lt=now)

        # Visibility filter
        visibility = self.request.query_params.get('visibility')
        if visibility == 'public':
            queryset = queryset.filter(is_public=True)
        elif visibility == 'private':
            queryset = queryset.filter(is_public=False)

        # Target type filter
        target_type = self.request.query_params.get('target_type')
        if target_type:
            queryset = queryset.filter(target_type=target_type)

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
    """Admin API for creating news items with file upload support"""
    serializer_class = NewsItemCreateSerializerAdmin
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
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


class AdminNewsDetailView(generics.RetrieveAPIView):
    """Admin API for viewing comprehensive news item details"""
    serializer_class = NewsItemAdminDetailSerializer
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


class AdminNewsUpdateView(generics.UpdateAPIView):
    """Admin API for updating news items with file upload support"""
    serializer_class = NewsItemUpdateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]
    lookup_field = 'id'
    queryset = NewsItem.objects.all()
    http_method_names = ['put', 'patch']

    def get_object(self):
        obj = get_object_or_404(NewsItem, id=self.kwargs.get('id'))
        if not is_admin_user(self.request.user):
            self.permission_denied(self.request, message="Admin access required")
        return obj

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated_instance = serializer.save()

        return Response({
            'success': True,
            'message': 'News item updated successfully',
            'data': serializer.to_representation(updated_instance)
        }, status=status.HTTP_200_OK)


# ADMIN FUNCTION-BASED VIEWS

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_targeting_options(request):
    """Get available targeting options for news creation"""
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    # Get available customers for targeting (limited for performance)
    customers = CustomUser.objects.filter(user_type='customer', is_active=True).values(
        'id', 'username', 'first_name', 'last_name', 'email'
    )[:100]

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_news_analytics(request, id):
    """Get detailed analytics for a news item"""
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)

    try:
        news_item = NewsItem.objects.select_related('target_user').prefetch_related('read_by', 'target_users').get(id=id)
    except NewsItem.DoesNotExist:
        return Response({'error': 'News item not found'}, status=status.HTTP_404_NOT_FOUND)

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
    ).order_by('-count')

    # Calculate engagement metrics
    total_reads = news_item.read_by.count()
    total_clicks = news_item.click_count

    # Calculate potential reach based on targeting
    potential_reach = 0
    if news_item.target_type == 'all' and news_item.is_public:
        potential_reach = CustomUser.objects.filter(user_type='customer', is_active=True).count()
    elif news_item.target_type == 'specific_user':
        potential_reach = 1
    elif news_item.target_type == 'user_group':
        potential_reach = news_item.target_users.count()
    elif news_item.target_type == 'customer_segment':
        # Estimate based on segment type
        segment_counts = {
            'vip': CustomUser.objects.filter(user_type='customer', is_active=True).count() * 0.1,
            'new': CustomUser.objects.filter(user_type='customer', is_active=True).count() * 0.2,
            'regular': CustomUser.objects.filter(user_type='customer', is_active=True).count() * 0.6,
            'inactive': CustomUser.objects.filter(user_type='customer', is_active=True).count() * 0.1,
        }
        potential_reach = int(segment_counts.get(news_item.target_customer_type, 100))

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