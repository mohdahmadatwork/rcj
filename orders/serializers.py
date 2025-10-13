# orders/serializers.py
from rest_framework import serializers
from .models import Order, OrderFile, OrderLog, Contact
from users.models import CustomUser
from django.contrib.auth import get_user_model
from django.utils import timezone


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

class CustomerOrderUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for customers to approve or decline their orders
    Only allows updating status to 'user_confirmed' or 'declined'
    """
    order_status = serializers.ChoiceField(
        choices=[
            ('user_confirmed', 'User Approved'),
            ('declined', 'Declined')
        ],
        required=True
    )
    declined_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Required when declining an order"
    )

    class Meta:
        model = Order
        fields = ['order_status', 'declined_reason']

    def validate(self, data):
        """
        Validate that declined_reason is provided when status is declined
        """
        order_status = data.get('order_status')
        declined_reason = data.get('declined_reason', '').strip()

        if order_status == 'declined' and not declined_reason:
            raise serializers.ValidationError({
                'declined_reason': 'Declined reason is required when declining an order.'
            })

        # Clear declined_reason if status is user_confirmed
        if order_status == 'user_confirmed':
            data['declined_reason'] = ''

        return data

    def validate_order_status(self, value):
        """
        Additional validation for order status
        """
        # Get the current order instance
        instance = self.instance
        if instance:
            current_status = instance.order_status
            
            # Only allow updates from specific statuses
            allowed_from_statuses = ['cad_done', 'new', 'confirmed']
            
            if current_status not in allowed_from_statuses:
                raise serializers.ValidationError(
                    f"Cannot update order status from '{current_status}'. "
                    f"Order must be in one of these statuses: {', '.join(allowed_from_statuses)}"
                )

        return value

class OrderAdminCreateSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Order
        fields = [
            'client_id','full_name', 'contact_number', 'email', 'description',
            'special_requirements', 'diamond_size', 'gold_weight',
            'preferred_delivery_date', 'address', 'files', 'gold_color'
        ]
    
    def create(self, validated_data):
        files_data = validated_data.pop('files', [])
        client_id = validated_data.get('client_id')
        user = self.context['request'].user
        customer = CustomUser.objects.get(client_id=client_id)
        # Set customer and client_id from authenticated user
        validated_data['customer'] = customer
        validated_data['client_id'] = customer.client_id
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


class OrderAdminFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    uploaded_by = serializers.SerializerMethodField()
    stage = serializers.SerializerMethodField() 
    type = serializers.SerializerMethodField()
    filename = serializers.SerializerMethodField()
    comment = serializers.CharField(source='description', read_only=True)

    class Meta:
        model = OrderFile
        fields = ['id', 'filename', 'url', 'type', 'stage', 'comment', 'uploaded_at', 'uploaded_by']

    def get_uploaded_by(self, obj):
        # Return 'admin' or 'customer' based on who uploaded
        return 'admin' if obj.uploaded_by and obj.uploaded_by.is_staff else 'customer'
    
    def get_stage(self, obj):
        # Map stage based on order status or file stage
        return getattr(obj, 'stage', 'initial')
    
    def get_type(self, obj):
        # Determine file type from filename or mime type
        if hasattr(obj, 'file') and obj.file:
            filename = str(obj.file).lower()
            if filename.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                return 'image'
            elif filename.endswith(('.mp4', '.avi', '.mov', '.wmv')):
                return 'video'
            elif filename.endswith(('.pdf', '.doc', '.docx')):
                return 'document'
        return 'image'  # default
    
    def get_filename(self, obj):
        if hasattr(obj, 'file') and obj.file:
            return obj.file.name.split('/')[-1]  # Get just the filename
        return f"file-{obj.id}"

    def get_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

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
            'user_confirmed':4,
            'rpt_done': 5,
            'casting': 6,
            'ready': 7,
            'delivered': 8,
        }
        return stage_mapping.get(obj.order_status, 1)


class OrderAdminStatusSerializer(serializers.ModelSerializer):
    # Match mockOrder field names exactly
    id = serializers.CharField(source='order_id', read_only=True)
    order_number = serializers.CharField(source='order_id', read_only=True)
    full_name = serializers.CharField(read_only=True)
    contact_number = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    description = serializers.CharField(read_only=True)
    special_requirements = serializers.CharField(read_only=True)
    diamond_size = serializers.CharField(read_only=True)
    gold_weight = serializers.CharField(read_only=True)
    gold_color = serializers.CharField(read_only=True)
    preferred_delivery_date = serializers.DateField(read_only=True)
    address = serializers.CharField(read_only=True)
    status = serializers.CharField(source='order_status', read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)
    estimated_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    notes = serializers.CharField(read_only=True)
    media = OrderAdminFileSerializer(source='files', many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'full_name',
            'contact_number',
            'email',
            'description',
            'special_requirements',
            'diamond_size',
            'gold_weight',
            'gold_color',
            'preferred_delivery_date',
            'address',
            'status',
            'created_at',
            'updated_at',
            'estimated_price',
            'final_price',
            'notes',
            'media',
            'declined_reason'
        ]
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


class ContactAdminSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(source='phone')
    is_related_to_order = serializers.BooleanField(source='order_related')
    related_order_id = serializers.CharField(source='order_id', allow_null=True)
    user_id = serializers.SerializerMethodField()
    is_registered_user = serializers.SerializerMethodField()
    priority = serializers.SerializerMethodField()
    ticket_number = serializers.CharField()
    status = serializers.SerializerMethodField()
    admin_notes = serializers.CharField(source='admin_response', allow_null=True, required=False)
    replied_at = serializers.DateTimeField(source='responded_at', allow_null=True, required=False)
    replied_by = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    class Meta:
        model = Contact
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'preferred_contact_method',
            'subject', 'message', 'is_related_to_order', 'related_order_id',
            'created_at', 'updated_at', 'status', 'priority', 'user_id',
            'is_registered_user', 'source', 'ticket_number',
            'admin_notes', 'replied_at', 'replied_by'
        ]

    def get_user_id(self, obj):
        return str(obj.user.username) if obj.user else None

    def get_is_registered_user(self, obj):
        return obj.user is not None

    def get_replied_by(self, obj):
        return obj.responded_by.username if obj.responded_by else None

    def get_status(self, obj):
        mapping = {
            'new': 'new',
            'in_progress': 'replied',
            'resolved': 'resolved',
            'closed': 'archived'
        }
        return mapping.get(obj.status, 'new')

    def get_priority(self, obj):
        score = 0
        # Order related
        if obj.order_related:
            score += 2
        # Recency
        hours = (timezone.now() - obj.created_at).total_seconds() / 3600
        if hours < 24:
            score += 2
        elif hours < 72:
            score += 1
        # Urgency keywords
        keywords = ['urgent', 'emergency', 'asap', 'immediately', 'help', 'problem', 'issue', 'error', 'delivery', 'missing']
        text = f"{obj.subject} {obj.message}".lower()
        if any(kw in text for kw in keywords):
            score += 1
        if score >= 4:
            return 'high'
        if score >= 2:
            return 'medium'
        return 'low'
    def get_source(self, obj):
        return 'website'

class ContactAdminUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Contact.STATUS_CHOICES, required=False)
    admin_response = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Contact
        fields = ['admin_response', 'status']

    def update(self, instance, validated_data):
        user = self.context['request'].user
        
        # Only update fields that are present in validated_data
        if 'admin_response' in validated_data:
            instance.admin_response = validated_data['admin_response']
            # Set responded_at and responded_by only when admin_response is provided and not already set
            if validated_data['admin_response'] and not instance.responded_at:
                instance.responded_at = timezone.now()
                instance.responded_by = user
        
        if 'status' in validated_data:
            instance.status = validated_data['status']
        
        instance.save()
        return instance
        
    def validate(self, data):
        # Ensure at least one field is being updated
        if not data:
            raise serializers.ValidationError("At least one field (admin_response or status) must be provided.")
        return data


class OrderAdminUpdateSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='order_status', required=False)
    estimated_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)
    special_requirements = serializers.CharField(required=False, allow_blank=True)
    preferred_delivery_date = serializers.DateField(required=False)
    diamond_size = serializers.CharField(required=False, allow_blank=True)
    gold_weight = serializers.CharField(required=False, allow_blank=True)
    gold_color = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    declined_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = [
            'status',
            'estimated_price', 
            'final_price',
            'notes',
            'special_requirements',
            'preferred_delivery_date',
            'diamond_size',
            'gold_weight',
            'gold_color',
            'description',
            'declined_reason'
        ]

    def validate_status(self, value):
        """Validate order status"""
        valid_statuses = [
            'new', 'confirmed', 'cad_done', 'user_confirmed' ,'rpt_done', 
            'casting', 'ready', 'delivered', 'declined'
        ]
        if value not in valid_statuses:
            raise serializers.ValidationError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return value

    def validate_estimated_price(self, value):
        """Validate estimated price is positive"""
        if value and value < 0:
            raise serializers.ValidationError("Estimated price must be positive")
        return value

    def validate_final_price(self, value):
        """Validate final price is positive"""
        if value and value < 0:
            raise serializers.ValidationError("Final price must be positive")
        return value

    def update(self, instance, validated_data):
        """Update only fields that are provided in the request"""
        
        # Handle status field mapping
        if 'order_status' in validated_data:
            instance.order_status = validated_data.pop('order_status')
        
        # Update other fields if provided
        for field, value in validated_data.items():
            if hasattr(instance, field):
                setattr(instance, field, value)
        
        instance.save()
        return instance

    def validate(self, data):
        """Ensure at least one field is being updated"""
        if not data:
            raise serializers.ValidationError("At least one field must be provided for update.")
        return data

class OrderAdminFileSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source='file.url', read_only=True)
    uploaded_by = serializers.SerializerMethodField()
    type = serializers.CharField(source='file_type', read_only=True)
    uploaded_at = serializers.DateTimeField(read_only=True)
    filename = serializers.SerializerMethodField()
    comment = serializers.CharField(source='caption', read_only=True)
    id = serializers.IntegerField(read_only=True)

    class Meta:
        model = OrderFile
        fields = ['id', 'filename', 'url', 'type', 'stage', 'comment', 'uploaded_at', 'uploaded_by']

    def get_uploaded_by(self, obj):
        # Return 'admin' or 'customer' based on who uploaded
        if obj.uploaded_by:
            return 'admin' if obj.uploaded_by.is_staff else 'customer'
        return 'customer'  # Default for files without uploaded_by
    
    def get_filename(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]  # Get just the filename
        return f"file-{obj.id}"
    



# orders/serializers.py (add these to your existing serializers)
from rest_framework import serializers
from .models import Message, Order

class MessageSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    sender = serializers.StringRelatedField(read_only=True)
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_type', 'sender', 'text', 'timestamp', 'is_read']
        read_only_fields = ['sender_type', 'sender', 'timestamp', 'is_read']

class MessageCreateSerializer(serializers.ModelSerializer):
    order_id = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Message
        fields = ['text', 'order_id']

    def validate_order_id(self, value):
        if value:
            try:
                order = Order.objects.get(order_id=value)
                # Check if user has access to this order
                user = self.context['request'].user
                if not user.is_staff and order.customer != user:
                    raise serializers.ValidationError("You don't have access to this order.")
                return order
            except Order.DoesNotExist:
                raise serializers.ValidationError("Order not found.")
        return None

    def create(self, validated_data):
        order = validated_data.pop('order_id', None)
        message = Message.objects.create(
            sender=self.context['request'].user,
            order=order,
            **validated_data
        )
        return message

class MessageListSerializer(serializers.ModelSerializer):
    id = serializers.CharField(read_only=True)
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    order_id = serializers.CharField(source='order.order_id', read_only=True)
    #  = serializers.StringRelatedField(read_only=True)
    sender = serializers.CharField(source='sender_type', required=False)

    class Meta:
        model = Message
        fields = ['id', 'sender', 'text', 'timestamp', 'is_read', 'order_id']
