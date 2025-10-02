# orders/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Order, OrderLog, Contact
from .serializers import (
    OrderCreateSerializer, OrderStatusSerializer, CustomerOrderListSerializer,
    OrderListSerializer, OrderUpdateSerializer, OrderLogSerializer, 
    ContactSerializer, ContactResponseSerializer
)
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

def is_admin_user(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and hasattr(user, 'user_type') and user.user_type == 'admin'

class OrderCreateView(generics.CreateAPIView):
    """Authenticated API for creating orders"""
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        # Ensure user has client_id
        if not request.user.client_id:
            request.user.save()  # This will generate client_id
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        
        return Response({
            'message': 'Order created successfully',
            'order_id': order.order_id,
            'client_id': order.client_id
        }, status=status.HTTP_201_CREATED)

class CustomerOrderListView(generics.ListAPIView):
    """Customer's own orders list"""
    serializer_class = CustomerOrderListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination
    def get_queryset(self):
        return Order.objects.filter(customer=self.request.user).order_by('-created_at')

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
    """Admin API for listing all orders"""
    serializer_class = OrderListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if not is_admin_user(self.request.user):
            return Order.objects.none()
        
        queryset = Order.objects.all().order_by('-created_at')
        
        # Search functionality
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(order_id__icontains=search) |
                Q(client_id__icontains=search) |
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(contact_number__icontains=search) |
                Q(customer__username__icontains=search)
            )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(order_status=status_filter)
            
        return queryset

class OrderDetailView(generics.RetrieveAPIView):
    """Admin API for viewing order details"""
    queryset = Order.objects.all()
    serializer_class = OrderStatusSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    
    def get_queryset(self):
        if not is_admin_user(self.request.user):
            return Order.objects.none()
        return Order.objects.all()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_decline_order(request, order_id):
    """Admin API for accepting or declining orders"""
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
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
@permission_classes([IsAuthenticated])
def update_order_status(request, order_id):
    """Admin API for updating order status"""
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
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
@permission_classes([IsAuthenticated])
def order_logs(request, order_id):
    """Admin API for viewing order change logs"""
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
    order = get_object_or_404(Order, order_id=order_id)
    logs = OrderLog.objects.filter(order=order).order_by('-timestamp')
    serializer = OrderLogSerializer(logs, many=True)
    return Response(serializer.data)

class AdminOrderCreateView(generics.CreateAPIView):
    """Admin API for creating orders"""
    queryset = Order.objects.all()
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def create(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save(created_by=request.user)
        
        return Response({
            'message': 'Order created successfully',
            'order_id': order.order_id,
            'client_id': order.client_id
        }, status=status.HTTP_201_CREATED)



@api_view(['POST'])
@permission_classes([AllowAny])  # Allow both anonymous and authenticated users
def contact_us(request):
    """
    Create a new contact/support request
    """
    serializer = ContactSerializer(data=request.data)
    
    if serializer.is_valid():
        contact_data = serializer.validated_data
        
        # Determine user assignment
        user_to_assign = None
        
        if request.user and request.user.is_authenticated:
            # If user is logged in, assign to them
            user_to_assign = request.user
        else:
            # Check if email matches an existing user
            try:
                user_to_assign = User.objects.get(email=contact_data['email'])
            except User.DoesNotExist:
                # Assign to user with ID 2 (admin/support user)
                try:
                    user_to_assign = User.objects.get(id=2)
                except User.DoesNotExist:
                    # Fallback to first admin user
                    user_to_assign = User.objects.filter(is_staff=True).first()
        
        # Create contact record
        contact = Contact.objects.create(
            user=user_to_assign,
            full_name=contact_data['full_name'],
            email=contact_data['email'],
            phone=contact_data['phone'],
            subject=contact_data['subject'],
            message=contact_data['message'],
            preferred_contact_method=contact_data['preferred_contact_method'],
            order_related=contact_data.get('order_related', False),
            order_id=contact_data.get('order_id', None),
        )
        
        # Serialize response
        response_serializer = ContactResponseSerializer(contact)
        
        # Optional: Send email notification to admin (you can add this later)
        # send_contact_notification_email.delay(contact.id)
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    # Return validation errors
    errors = []
    for field, messages in serializer.errors.items():
        for message in messages:
            errors.append({
                'field': field,
                'message': str(message)
            })
    
    return Response(
        {'errors': errors},
        status=status.HTTP_400_BAD_REQUEST
    )

# Optional: Get user's contact history (for authenticated users)
@api_view(['GET'])
def my_contact_requests(request):
    """
    Get current user's contact requests
    """
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    contacts = Contact.objects.filter(user=request.user)
    
    # Simple serialization for listing
    data = []
    for contact in contacts:
        data.append({
            'id': str(contact.id),
            'ticket_number': contact.ticket_number,
            'subject': contact.subject,
            'status': contact.status,
            'order_related': contact.order_related,
            'order_id': contact.order_id,
            'created_at': contact.created_at.isoformat(),
            'admin_response': contact.admin_response,
            'responded_at': contact.responded_at.isoformat() if contact.responded_at else None,
        })
    
    return Response(data, status=status.HTTP_200_OK)
