# orders/views.py
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db.models import Count, Sum, Avg, Q
from .models import Order, OrderLog, Contact, OrderFile
from .serializers import (
    OrderCreateSerializer, OrderStatusSerializer, CustomerOrderListSerializer,
    OrderListSerializer, OrderUpdateSerializer, OrderLogSerializer, 
    ContactSerializer, ContactResponseSerializer, AdminOrderListSerializer, 
    ContactAdminSerializer, ContactAdminUpdateSerializer, OrderAdminStatusSerializer, OrderAdminUpdateSerializer
)
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
import random
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

def is_admin_user(user):
    """Helper function to check if user is admin"""
    return user.is_authenticated and hasattr(user, 'user_type') and user.user_type.lower() == 'admin'

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
    serializer_class = AdminOrderListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination


    def get_queryset(self):
        user = self.request.user
        if not is_admin_user(user):
            return Order.objects.none()

        qs = Order.objects.all().order_by('-created_at')

        # Search
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(order_id__icontains=search) |
                Q(client_id__icontains=search) |
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(contact_number__icontains=search) |
                Q(customer__username__icontains=search)
            )

        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(order_status=status_filter)

        return qs

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

class OrderAdminDetailView(generics.RetrieveAPIView):
    """Admin API for viewing order details"""
    serializer_class = OrderAdminStatusSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    queryset = Order.objects.all()
    
    def get_queryset(self):
        if not is_admin_user(self.request.user):
            return Order.objects.none()
        return Order.objects.select_related().prefetch_related('files')
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'data': serializer.data  # Use 'data' to match mockOrder structure
        }, status=status.HTTP_200_OK)


# Alternative function-based approach
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def order_detail(request, order_id):
    """Admin API for getting order details (function-based alternative)"""
    
    if not is_admin_user(request.user):
        return Response({'error': 'Admin access required'}, status=status.HTTP_403_FORBIDDEN)
    
    try:
        order = Order.objects.select_related().prefetch_related('files').get(order_id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Order not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = OrderStatusSerializer(order)
    
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_200_OK)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def admin_dashboard_stats(request):
    """
    Get comprehensive dashboard statistics for admin
    """
    try:
        # Get date ranges
        today = timezone.now().date()
        this_month_start = today.replace(day=1)
        last_30_days = today - timedelta(days=30)
        
        # Order Statistics
        total_orders = Order.objects.count()
        new_orders = Order.objects.filter(order_status='new').count()
        pending_orders = Order.objects.filter(
            order_status__in=['confirmed', 'cad_done', 'rpt_done', 'casting']
        ).count()
        completed_orders = Order.objects.filter(order_status='delivered').count()
        cancelled_orders = Order.objects.filter(order_status='declined').count()
        todays_deliveries = Order.objects.filter(
            order_status='delivered',
            updated_at__date=today
        ).count()
        
        # Revenue (sum of estimated_value for delivered orders)
        monthly_revenue = Order.objects.filter(
            order_status='delivered',
            created_at__gte=this_month_start
        ).aggregate(
            total=Sum('estimated_value')
        )['total'] or 0.0
        
        # Recent Orders (last 10)
        recent_orders_qs = Order.objects.select_related('customer').order_by('-created_at')[:10]
        recent_orders = []
        
        for order in recent_orders_qs:
            # Assign random priority since it's not in model
            priority = random.choice(['low', 'medium', 'high', 'urgent'])
            
            recent_orders.append({
                'id': order.order_id,
                'customer_name': order.full_name,
                'jewelry_type': order.description[:50] + '...' if len(order.description) > 50 else order.description,
                'status': order.order_status,
                'total_amount': float(order.estimated_value),
                'created_at': order.created_at.isoformat(),
                'priority': priority
            })
        
        # Recent Contacts (last 10)
        recent_contacts_qs = Contact.objects.order_by('-created_at')[:10]
        recent_contacts = []
        
        for contact in recent_contacts_qs:
            # Map contact status to expected format
            status_mapping = {
                'new': 'new',
                'in_progress': 'in-progress',
                'resolved': 'resolved',
                'closed': 'resolved'
            }
            
            recent_contacts.append({
                'id': str(contact.id),
                'customer_name': contact.full_name,
                'email': contact.email,
                'subject': contact.subject,
                'status': status_mapping.get(contact.status, 'new'),
                'created_at': contact.created_at.isoformat(),
                'category': 'Order Related' if contact.order_related else 'General Inquiry'
            })
        
        # Performance Metrics
        total_delivered = Order.objects.filter(order_status='delivered').count()
        completion_rate = (total_delivered / total_orders * 100) if total_orders > 0 else 0.0
        
        avg_order_value = Order.objects.filter(
            order_status='delivered',
            estimated_value__gt=0
        ).aggregate(
            avg=Avg('estimated_value')
        )['avg'] or 0.0
        
        # Default customer satisfaction (you can implement this with a rating system later)
        customer_satisfaction = 4.2  # Default value
        
        # Order Trends (last 30 days)
        order_trends = []
        for i in range(30):
            date = today - timedelta(days=i)
            orders_count = Order.objects.filter(created_at__date=date).count()
            revenue = Order.objects.filter(
                order_status='delivered',
                created_at__date=date
            ).aggregate(
                total=Sum('estimated_value')
            )['total'] or 0.0
            
            order_trends.append({
                'date': date.isoformat(),
                'orders_count': orders_count,
                'revenue': float(revenue)
            })
        
        # Reverse to get chronological order
        order_trends.reverse()
        
        # Revenue Trends (last 12 months)
        revenue_trends = []
        for i in range(12):
            # Calculate month start
            if today.month - i <= 0:
                month = today.month - i + 12
                year = today.year - 1
            else:
                month = today.month - i
                year = today.year
            
            month_start = datetime(year, month, 1).date()
            if month == 12:
                month_end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
            else:
                month_end = datetime(year, month + 1, 1).date() - timedelta(days=1)
            
            month_orders = Order.objects.filter(
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).count()
            
            month_revenue = Order.objects.filter(
                order_status='delivered',
                created_at__date__gte=month_start,
                created_at__date__lte=month_end
            ).aggregate(
                total=Sum('estimated_value')
            )['total'] or 0.0
            
            month_name = datetime(year, month, 1).strftime('%b %Y')
            
            revenue_trends.append({
                'month': month_name,
                'revenue': float(month_revenue),
                'orders': month_orders
            })
        
        # Reverse to get chronological order
        revenue_trends.reverse()
        
        # Prepare response data
        dashboard_data = {
            # Order Statistics
            'total_orders': total_orders,
            'new_orders': new_orders,
            'pending_orders': pending_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'todays_deliveries': todays_deliveries,
            'monthly_revenue': float(monthly_revenue),
            
            # Recent Activity
            'recent_orders': recent_orders,
            'recent_contacts': recent_contacts,
            
            # Performance Metrics
            'completion_rate': round(completion_rate, 2),
            'avg_order_value': round(float(avg_order_value), 2),
            'customer_satisfaction': customer_satisfaction,
            
            # Trends
            'order_trends': order_trends,
            'revenue_trends': revenue_trends
        }
        
        return Response({
            'success': True,
            'data': dashboard_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': 'Failed to fetch dashboard statistics',
            'details': [str(e)]
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Add this to your views.py file

class AdminContactListView(generics.ListAPIView):
    """
    Admin API for listing all contact inquiries.
    """
    serializer_class = ContactAdminSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        user = self.request.user
        if not is_admin_user(user):
            return Contact.objects.none()

        qs = (
            Contact.objects
            .select_related('user', 'related_order', 'responded_by')
            .order_by('-created_at')
        )

        # Search across relevant fields
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(ticket_number__icontains=search) |
                Q(full_name__icontains=search) |
                Q(email__icontains=search) |
                Q(phone__icontains=search) |
                Q(subject__icontains=search) |
                Q(order_id__icontains=search)
            )

        # Status filter
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Order-related filter
        order_related = self.request.query_params.get('order_related')
        if order_related is not None:
            qs = qs.filter(order_related=order_related.lower() == 'true')

        return qs


class AdminContactUpdateView(generics.UpdateAPIView):
    """Admin API for updating a contact inquiry"""
    serializer_class = ContactAdminUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'
    queryset = Contact.objects.all()

    def get_object(self):
        obj = get_object_or_404(Contact, id=self.kwargs.get('id'))
        if not is_admin_user(self.request.user):
            self.permission_denied(self.request, message="Admin access required")
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Set responded_at and responded_by if admin_response added
        if 'admin_response' in serializer.validated_data and not instance.responded_at:
            instance.responded_at = timezone.now()
            instance.responded_by = request.user
        self.perform_update(serializer)
        # Return full serialized contact data
        return Response({
            'success': True,
            'result': ContactAdminSerializer(instance).data
        }, status=status.HTTP_200_OK)


class OrderAdminUpdateView(generics.UpdateAPIView):
    """Admin API for updating order details with file upload support"""
    serializer_class = OrderAdminUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    queryset = Order.objects.all()
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        obj = get_object_or_404(Order, order_id=self.kwargs.get('order_id'))
        if not is_admin_user(self.request.user):
            self.permission_denied(self.request, message="Admin access required")
        return obj

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Handle file uploads separately
        uploaded_files = request.FILES.getlist('files')
        file_captions = request.data.getlist('file_captions', [])  # Changed from file_comments
        file_stages = request.data.getlist('file_stages', [])
        
        # Update order fields
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Handle file uploads
        if uploaded_files:
            self.handle_file_uploads(instance, uploaded_files, file_captions, file_stages, request.user)
        
        # Return updated order with media
        instance.refresh_from_db()
        response_serializer = OrderStatusSerializer(instance)
        return Response({
            'success': True,
            'message': 'Order updated successfully',
            'data': response_serializer.data,
            'files_uploaded': len(uploaded_files)
        }, status=status.HTTP_200_OK)

    def handle_file_uploads(self, order, files, captions, stages, user):
        """Handle multiple file uploads"""
        for i, file in enumerate(files):
            # Validate file type
            if not self.is_valid_file_type(file):
                continue
                
            # Get caption and stage for this file
            caption = captions[i] if i < len(captions) else ''
            stage = stages[i] if i < len(stages) else order.order_status
            
            # Create OrderFile record using your model fields
            OrderFile.objects.create(
                order=order,
                file=file,
                caption=caption,  # Using caption instead of description
                stage=stage,
                uploaded_by=user,
                file_type=self.get_file_type(file)
            )

    def is_valid_file_type(self, file):
        """Validate file type and size"""
        # Max file size: 10MB
        max_size = 10 * 1024 * 1024
        if file.size > max_size:
            return False
        
        # Allowed extensions - matching your model choices
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
            '.mp4', '.avi', '.mov', '.wmv', '.mkv',    # Videos
        ]
        
        file_extension = '.' + file.name.split('.')[-1].lower()
        return file_extension in allowed_extensions

    def get_file_type(self, file):
        """Determine file type - matching your model choices"""
        file_extension = '.' + file.name.split('.')[-1].lower()
        
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return 'image'
        elif file_extension in ['.mp4', '.avi', '.mov', '.wmv', '.mkv']:
            return 'video'
        return 'image'  # Default to image as per your model