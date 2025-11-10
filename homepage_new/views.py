from rest_framework import generics, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, WorkSample
from .serializers import (
    CategorySerializer,
    WorkSampleListSerializer,
    WorkSampleDetailSerializer,
    WorkSampleCreateUpdateSerializer
)


class WorkSamplePagination(PageNumberPagination):
    """Custom pagination for work samples"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class CategoryListView(generics.ListAPIView):
    """List all categories with work sample counts"""
    serializer_class = CategorySerializer
    
    def get_queryset(self):
        return Category.objects.annotate(
            work_samples_count=Count('work_samples', filter=Q(work_samples__is_active=True))
        )


class CategoryDetailView(generics.RetrieveAPIView):
    """Retrieve a single category by ID"""
    serializer_class = CategorySerializer
    lookup_field = 'pk'  # Changed from 'slug' to 'pk'
    
    def get_queryset(self):
        return Category.objects.annotate(
            work_samples_count=Count('work_samples', filter=Q(work_samples__is_active=True))
        )


class WorkSampleListView(generics.ListAPIView):
    """List all work samples with filtering and search"""
    serializer_class = WorkSampleListSerializer
    pagination_class = WorkSamplePagination
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_featured', 'is_active']
    search_fields = ['title', 'description']
    ordering_fields = ['display_order', 'created_at', 'title']
    ordering = ['display_order', '-created_at']

    def get_queryset(self):
        queryset = WorkSample.objects.all().select_related('category')
        
        # Filter by category if provided
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter featured items if requested
        featured = self.request.query_params.get('featured', None)
        if featured is not None:
            queryset = queryset.filter(is_featured=True)
        
        return queryset


class WorkSampleDetailView(generics.RetrieveAPIView):
    """Retrieve a single work sample by ID"""
    queryset = WorkSample.objects.all().select_related('category')
    serializer_class = WorkSampleDetailSerializer
    lookup_field = 'pk'  # Changed from 'slug' to 'pk'
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


class WorkSampleCreateView(generics.CreateAPIView):
    """Create a new work sample"""
    queryset = WorkSample.objects.all()
    serializer_class = WorkSampleCreateUpdateSerializer
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()


class WorkSampleUpdateView(generics.UpdateAPIView):
    """Update an existing work sample by ID"""
    queryset = WorkSample.objects.all()
    serializer_class = WorkSampleCreateUpdateSerializer
    lookup_field = 'pk'  # Changed from 'slug' to 'pk'
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]


class WorkSampleDeleteView(generics.DestroyAPIView):
    """Delete a work sample by ID"""
    queryset = WorkSample.objects.all()
    lookup_field = 'pk'  # Changed from 'slug' to 'pk'
    # authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]


class PortfolioOverviewView(APIView):
    """Get portfolio overview with all work samples grouped by category"""
    
    def get(self, request):
        categories = Category.objects.prefetch_related(
            'work_samples'
        ).annotate(
            work_samples_count=Count('work_samples', filter=Q(work_samples__is_active=True))
        )
        
        overview_data = {
            'title': 'Our Work Samples',
            'subtitle': 'Explore our portfolio of exceptional manufacturing projects that showcase our commitment to quality, precision, and innovation across various industries.',
            'categories': []
        }
        
        for category in categories:
            work_samples = category.work_samples.filter(is_active=True)
            category_data = {
                'id': category.id,
                'name': category.name,
                'slug': category.slug,
                'description': category.description,
                'work_samples_count': work_samples.count(),
                'work_samples': WorkSampleListSerializer(
                    work_samples,
                    many=True,
                    context={'request': request}
                ).data
            }
            overview_data['categories'].append(category_data)
        
        return Response(overview_data, status=status.HTTP_200_OK)



class PublicWorkSampleListView(generics.ListAPIView):
    """Public API for client-side - shows only active work samples without pagination"""
    serializer_class = WorkSampleListSerializer
    authentication_classes = []  # No authentication required
    permission_classes = []  # Public access
    pagination_class = None  # Disable pagination
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category__slug', 'is_featured']
    search_fields = ['title', 'description']
    ordering_fields = ['display_order', 'created_at', 'title']
    ordering = ['display_order', '-created_at']

    def get_queryset(self):
        # Only return active work samples for public
        queryset = WorkSample.objects.filter(is_active=True).select_related('category')
        
        # Filter by category if provided
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter featured items if requested
        featured = self.request.query_params.get('featured', None)
        if featured is not None:
            queryset = queryset.filter(is_featured=True)
        
        return queryset


class CategoryDetailView(generics.RetrieveAPIView):
    """Get category by ID - Public endpoint"""
    serializer_class = CategorySerializer
    authentication_classes = []
    permission_classes = []
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Category.objects.annotate(
            work_samples_count=Count('work_samples', filter=Q(work_samples__is_active=True))
        )


class CategoryCreateView(generics.CreateAPIView):
    """Create new category - Admin only"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        serializer.save()


class CategoryUpdateView(generics.UpdateAPIView):
    """Update category by ID - Admin only"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'pk'
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]


class CategoryDeleteView(generics.DestroyAPIView):
    """Delete category by ID - Admin only"""
    queryset = Category.objects.all()
    lookup_field = 'pk'
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]
