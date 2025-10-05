# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderFile, OrderLog, Contact
from django.contrib.auth import get_user_model

User = get_user_model()

class OrderFileSerializer(serializers.ModelSerializer):
    fileType = serializers.CharField(source='file_type', read_only=True)
    uploadedAt = serializers.CharField(source='uploaded_at', read_only=True)
    url = serializers.SerializerMethodField()
    
    class Meta:
        model = OrderFile
        fields = ['id', 'url', 'caption', 'stage', 'uploadedAt', 'fileType']
    
    def get_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

class OrderCreateSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Order
        fields = [
            'full_name', 'contact_number', 'email', 'description',
            'special_requirements', 'diamond_size', 'gold_weight',
            'preferred_delivery_date', 'address', 'files', 'gold_color'
        ]
    
    def create(self, validated_data):
        files_data = validated_data.pop('files', [])
        user = self.context['request'].user
        
        # Set customer and client_id from authenticated user
        validated_data['customer'] = user
        validated_data['client_id'] = user.client_id
        
        order = Order.objects.create(**validated_data)
        
        for file_data in files_data:
            file_type = 'image' if file_data.content_type.startswith('image') else 'video'
            OrderFile.objects.create(
                order=order,
                file=file_data,
                file_type=file_type,
                stage='initial'
            )
        
        return order

class CustomerOrderListSerializer(serializers.ModelSerializer):
    """Serializer for customer's order list"""
    class Meta:
        model = Order
        fields = [
            'order_id', 'client_id', 'full_name', 'order_status', 
            'created_at', 'preferred_delivery_date', 'gold_color'
        ]

class OrderStatusSerializer(serializers.ModelSerializer):
    orderId = serializers.CharField(source='order_id', read_only=True)
    clientId = serializers.CharField(source='client_id', read_only=True)
    partyName = serializers.CharField(source='full_name', read_only=True)
    orderDate = serializers.DateTimeField(source='created_at', read_only=True)
    expectedDelivery = serializers.DateField(source='preferred_delivery_date', read_only=True)
    contact = serializers.CharField(source='contact_number', read_only=True)
    status = serializers.CharField(source='order_status', read_only=True)
    currentStage = serializers.SerializerMethodField()
    description = serializers.CharField(read_only=True)
    declinedReason = serializers.CharField(source='declined_reason', read_only=True)
    specialRequirements = serializers.CharField(source='special_requirements', read_only=True)
    diamondSize = serializers.CharField(source='diamond_size', read_only=True)
    goldWeight = serializers.CharField(source='gold_weight', read_only=True)
    # estimatedValue = serializers.CharField(source='estimated_value', read_only=True)
    address = serializers.CharField(read_only=True)
    images = OrderFileSerializer(source='files', many=True, read_only=True)
    goldColor = serializers.CharField(source='gold_color', read_only=True)
    class Meta:
        model = Order
        fields = [
            'orderId',
            'clientId',
            'partyName',
            'orderDate',
            'expectedDelivery',
            'contact',
            'email',
            'address',
            'status',
            'currentStage',
            'description',
            'specialRequirements',
            'diamondSize',
            'goldWeight',
            # 'estimatedValue',
            'images',
            'declinedReason',
            'goldColor',
        ]

    def get_currentStage(self, obj):
        stage_mapping = {
            'declined': 0,
            'new': 1,
            'confirmed': 2,
            'cad_done': 3,
            'rpt_done': 4,
            'casting': 5,
            'ready': 6,
            'delivered': 7,
        }
        return stage_mapping.get(obj.order_status, 1)

# Admin serializers remain the same
class OrderListSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.username', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'order_id', 'client_id', 'customer_name', 'full_name', 
            'contact_number', 'email', 'order_status', 'created_at', 
            'preferred_delivery_date', 'estimated_value'
        ]

class OrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['order_status', 'declined_reason', 'estimated_value', 'address']

class OrderLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = OrderLog
        fields = ['action', 'changes', 'timestamp', 'user_name']



class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = [
            'full_name', 'email', 'phone', 'subject', 'message',
            'preferred_contact_method', 'order_related', 'order_id'
        ]
    
    def validate(self, data):
        # If order_related is True, order_id should be provided
        if data.get('order_related') and not data.get('order_id'):
            raise serializers.ValidationError({
                'order_id': 'Order ID is required when the inquiry is order-related.'
            })
        
        # Validate order_id exists if provided
        if data.get('order_id'):
            try:
                Order.objects.get(order_id=data['order_id'])
            except Order.DoesNotExist:
                raise serializers.ValidationError({
                    'order_id': 'Invalid order ID provided.'
                })
        
        return data

class ContactResponseSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    ticket_number = serializers.CharField(read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ['id', 'message', 'ticket_number']
    
    def get_message(self, obj):
        return f"Your contact request has been submitted successfully. Ticket Number: {obj.ticket_number}"


# orders/serializers.py
from rest_framework import serializers
from .models import Order

class AdminOrderListSerializer(serializers.ModelSerializer):
    id              = serializers.CharField(source='pk')
    order_number    = serializers.CharField(source='order_id')
    estimated_price = serializers.CharField(source='estimated_value')
    final_price     = serializers.FloatField(default=2.0)
    status          = serializers.CharField(source='order_status')
    notes           = serializers.CharField(default='', allow_blank=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'full_name', 'contact_number', 'email',
            'description', 'special_requirements', 'diamond_size',
            'gold_weight', 'gold_color', 'preferred_delivery_date',
            'address', 'status', 'created_at', 'updated_at',
            'estimated_price', 'final_price', 'notes'
        ]
