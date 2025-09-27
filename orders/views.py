# orders/views.py
from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from .models import Order, OrderLog
from .serializers import (
    OrderCreateSerializer, OrderStatusSerializer, OrderListSerializer,
    OrderUpdateSerializer, OrderLogSerializer
)
from .permissions import IsAdmin
import json

class OrderCreateView(generics.CreateAPIView):
    """Public API for creating orders"""
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        return Response({
            'message': 'Order created successfully',
            'order_id': order.order_id,
            'client_id': order.client_id
        }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def check_order_status(request):
    """Public API for checking order status"""
    order_id = request.GET.get('order_id')
    client_id = request.GET.get('client_id')
    
    if not order_id or not client_id:
        return Response(
            {'error': 'Both order_id and client_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        order = Order.objects.get(order_id=order_id, client_id=client_id)
        serializer = OrderStatusSerializer(order)
        return Response(serializer.data)
    except Order.DoesNotExist:
        return Response(
            {'error': 'Order not found'},
            status=status.HTTP_404_NOT_FOUND
        )

class OrderListView(generics.ListAPIView):
    """Admin API for listing all orders with search and filter"""
    queryset = Order.objects.all().order_by('-created_at')
    serializer_class = OrderListSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['order_status', 'created_at']
    search_fields = ['order_id', 'client_id', 'full_name', 'email', 'contact_number']
    ordering_fields = ['created_at', 'preferred_delivery_date', 'estimated_value']

class OrderDetailView(generics.RetrieveAPIView):
    """Admin API for viewing order details"""
    queryset = Order.objects.all()
    serializer_class = OrderStatusSerializer
    permission_classes = [IsAdmin]
    lookup_field = 'order_id'

@api_view(['POST'])
@permission_classes([IsAdmin])
def accept_decline_order(request, order_id):
    """Admin API for accepting or declining orders"""
    order = get_object_or_404(Order, order_id=order_id)
    action = request.data.get('action')  # 'accept' or 'decline'
    declined_reason = request.data.get('declined_reason', '')
    
    if action == 'accept':
        old_status = order.order_status
        order.order_status = 'cad_done'
        order.save()
        
        # Log the change
        OrderLog.objects.create(
            order=order,
            user=request.user,
            action=f'Order accepted and moved to CAD stage',
            changes={'old_status': old_status, 'new_status': 'cad_done'}
        )
        
        return Response({'message': 'Order accepted successfully'})
    
    elif action == 'decline':
        old_status = order.order_status
        order.order_status = 'declined'
        order.declined_reason = declined_reason
        order.save()
        
        # Log the change
        OrderLog.objects.create(
            order=order,
            user=request.user,
            action=f'Order declined',
            changes={
                'old_status': old_status, 
                'new_status': 'declined',
                'declined_reason': declined_reason
            }
        )
        
        return Response({'message': 'Order declined successfully'})
    
    else:
        return Response(
            {'error': 'Invalid action. Use "accept" or "decline"'},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['PUT'])
@permission_classes([IsAdmin])
def update_order_status(request, order_id):
    """Admin API for updating order status"""
    order = get_object_or_404(Order, order_id=order_id)
    serializer = OrderUpdateSerializer(order, data=request.data, partial=True)
    
    if serializer.is_valid():
        old_data = {
            'status': order.order_status,
            'estimated_value': str(order.estimated_value),
            'address': order.address
        }
        
        serializer.save()
        
        # Log the change
        changes = {}
        for field in ['order_status', 'estimated_value', 'address']:
            old_value = old_data.get(field.replace('order_', '') if field.startswith('order_') else field)
            new_value = getattr(order, field)
            if str(old_value) != str(new_value):
                changes[field] = {'old': old_value, 'new': str(new_value)}
        
        if changes:
            OrderLog.objects.create(
                order=order,
                user=request.user,
                action='Order updated',
                changes=changes
            )
        
        return Response(serializer.data)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAdmin])
def order_logs(request, order_id):
    """Admin API for viewing order change logs"""
    order = get_object_or_404(Order, order_id=order_id)
    logs = OrderLog.objects.filter(order=order).order_by('-timestamp')
    serializer = OrderLogSerializer(logs, many=True)
    return Response(serializer.data)

class AdminOrderCreateView(generics.CreateAPIView):
    """Admin API for creating orders"""
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser]
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

