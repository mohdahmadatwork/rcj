# users/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from orders.models import Order
from .serializers import (
    UserRegistrationSerializer, 
    UserLoginSerializer, 
    UserProfileSerializer,
    UserDetailSerializer
)

User = get_user_model()

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        
        user_serializer = UserDetailSerializer(user)
        
        return Response({
            'token': token.key,
            'user': user_serializer.data
        }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
@permission_classes([AllowAny])
def user_login(request):
    serializer = UserLoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        user_serializer = UserDetailSerializer(user)
        
        return Response({
            'token': token.key,
            'user': user_serializer.data
        })
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def user_logout(request):
    """
    Logout API - Supports both POST and DELETE methods
    Deletes the user's authentication token
    """
    try:
        # Delete the user's token
        token = Token.objects.get(user=request.user)
        token.delete()
        
        return Response({
            'message': 'Logout successful',
            'success': True
        }, status=status.HTTP_200_OK)
    except Token.DoesNotExist:
        return Response({
            'message': 'User was already logged out',
            'success': True
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'message': 'Error logging out',
            'error': str(e),
            'success': False
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def customer_dashboard(request):
    """
    Customer Dashboard API
    Returns user profile, order statistics, and recent orders
    """
    user = request.user
    
    # Get user's orders
    user_orders = Order.objects.filter(customer=user)
    
    # Calculate order statistics
    order_stats = user_orders.aggregate(
        total_orders=Count('id'),
        new_orders=Count('id', filter=Q(order_status='new')),
        cad_done_orders=Count('id', filter=Q(order_status='cad_done')),
        rpt_done_orders=Count('id', filter=Q(order_status='rpt_done')),
        casting_orders=Count('id', filter=Q(order_status='casting')),
        ready_orders=Count('id', filter=Q(order_status='ready')),
        delivered_orders=Count('id', filter=Q(order_status='delivered')),
        declined_orders=Count('id', filter=Q(order_status='declined'))
    )
    
    # Get recent orders (last 5)
    recent_orders = user_orders.order_by('-created_at')[:5]
    recent_orders_data = []
    
    for order in recent_orders:
        recent_orders_data.append({
            'order_id': order.order_id,
            'client_id': order.client_id,
            'full_name': order.full_name,
            'order_status': order.order_status,
            'created_at': order.created_at,
            'preferred_delivery_date': order.preferred_delivery_date,
            'estimated_value': str(order.estimated_value),
            'current_stage': get_order_stage(order.order_status)
        })
    
    # Get orders by status for quick access
    orders_by_status = {
        'new': user_orders.filter(order_status='new').count(),
        'in_progress': user_orders.filter(
            order_status__in=['cad_done', 'rpt_done', 'casting']
        ).count(),
        'ready': user_orders.filter(order_status='ready').count(),
        'delivered': user_orders.filter(order_status='delivered').count(),
        'declined': user_orders.filter(order_status='declined').count()
    }
    
    # User profile data
    user_serializer = UserDetailSerializer(user)
    
    dashboard_data = {
        'user': user_serializer.data,
        'client_id': user.client_id,
        'statistics': {
            'total_orders': order_stats['total_orders'] or 0,
            'orders_by_status': orders_by_status,
            'detailed_status': {
                'new': order_stats['new_orders'] or 0,
                'cad_done': order_stats['cad_done_orders'] or 0,
                'rpt_done': order_stats['rpt_done_orders'] or 0,
                'casting': order_stats['casting_orders'] or 0,
                'ready': order_stats['ready_orders'] or 0,
                'delivered': order_stats['delivered_orders'] or 0,
                'declined': order_stats['declined_orders'] or 0
            }
        },
        'recent_orders': recent_orders_data,
        'quick_stats': {
            'pending_orders': orders_by_status['new'] + orders_by_status['in_progress'],
            'completed_orders': orders_by_status['delivered'],
            'ready_for_pickup': orders_by_status['ready']
        }
    }
    
    return Response(dashboard_data, status=status.HTTP_200_OK)

def get_order_stage(order_status):
    """Helper function to get order stage number"""
    stage_mapping = {
        'new': 1,
        'cad_done': 2,
        'rpt_done': 3,
        'casting': 4,
        'ready': 5,
        'delivered': 6,
        'declined': 0
    }
    return stage_mapping.get(order_status, 1)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
