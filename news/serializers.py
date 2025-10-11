# news/serializers.py
from rest_framework import serializers
from .models import NewsItem, NewsReadTracker
from users.models import CustomUser

class NewsItemListSerializer(serializers.ModelSerializer):
    isRead = serializers.SerializerMethodField()
    isPublic = serializers.BooleanField(source='is_public', read_only=True)
    imageUrl = serializers.CharField(source='image_url', read_only=True)
    publishedAt = serializers.CharField(source='published_at', read_only=True)
    expiresAt = serializers.CharField(source='expires_at', read_only=True)
    actionButton = serializers.JSONField(source='action_button', read_only=True)
    
    class Meta:
        model = NewsItem
        fields = [
            'id','title','excerpt','category','priority','author',
            'publishedAt','expiresAt','imageUrl','isPublic',
            'target_user','isRead','tags','actionButton'
        ]
    
    def get_isRead(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return obj.read_by.filter(id=user.id).exists()



class NewsItemDetailSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()
    target_user_id = serializers.PrimaryKeyRelatedField(
        source='target_user', read_only=True
    )

    class Meta:
        model = NewsItem
        fields = [
            'id','title','content','excerpt','category','priority','author',
            'published_at','expires_at','image_url','is_public','target_user_id',
            'is_read','tags','action_button'
        ]

    def get_is_read(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return obj.read_by.filter(id=user.id).exists()


# Add this to serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import NewsItem

class NewsItemAdminSerializer(serializers.ModelSerializer):
    # Map fields to match frontend structure
    publishedAt = serializers.DateTimeField(source='published_at', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    expiresAt = serializers.DateTimeField(source='expires_at', allow_null=True)
    imageUrl = serializers.URLField(source='image_url', allow_null=True)
    isPublic = serializers.BooleanField(source='is_public')
    
    # Target user information
    targetUserId = serializers.SerializerMethodField()
    targetUserEmail = serializers.SerializerMethodField()
    
    # Author information
    authorId = serializers.SerializerMethodField()
    
    # Status based on published_at
    status = serializers.SerializerMethodField()
    
    # Read and click counts
    readCount = serializers.SerializerMethodField()
    clickCount = serializers.SerializerMethodField()
    
    # Action button as JSON
    actionButton = serializers.JSONField(source='action_button', allow_null=True)

    class Meta:
        model = NewsItem
        fields = [
            'id', 'title', 'content', 'excerpt', 'category', 'priority', 'status',
            'author', 'authorId', 'publishedAt', 'createdAt', 'updatedAt', 
            'expiresAt', 'imageUrl', 'isPublic', 'targetUserId', 'targetUserEmail',
            'tags', 'actionButton', 'readCount', 'clickCount'
        ]

    def get_targetUserId(self, obj):
        return str(obj.target_user.id) if obj.target_user else None

    def get_targetUserEmail(self, obj):
        return obj.target_user.email if obj.target_user else None

    def get_authorId(self, obj):
        # Generate author ID from author name or use a default pattern
        if obj.author:
            return obj.author.lower().replace(' ', '_').replace('team', 'team_1')
        return 'admin_1'

    def get_status(self, obj):
        if not obj.published_at:
            return 'draft'
        elif obj.published_at <= timezone.now():
            return 'published'
        else:
            return 'scheduled'

    def get_readCount(self, obj):
        return obj.read_by.count()

    def get_clickCount(self, obj):
        # If you track click counts, implement here
        # For now, return a placeholder or 0
        return 0


class NewsItemCreateSerializerAdmin(serializers.ModelSerializer):
    # Optional fields for targeting
    target_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = NewsItem
        fields = [
            'title', 'content', 'excerpt', 'category', 'priority', 'author',
            'published_at', 'expires_at', 'image_url', 'is_public',
            'target_type', 'target_user_id', 'target_user_ids',
            'target_customer_type', 'target_order_status', 
            'tags', 'action_button', 'related_order_id'
        ]

    def validate_published_at(self, value):
        """Validate published_at is not in the past for scheduled news"""
        if value and value < timezone.now():
            # Allow past dates for immediate publishing
            pass
        return value

    def validate_expires_at(self, value):
        """Validate expires_at is after published_at"""
        published_at = self.initial_data.get('published_at')
        if value and published_at:
            try:
                pub_date = serializers.DateTimeField().to_internal_value(published_at)
                if value <= pub_date:
                    raise serializers.ValidationError("Expiry date must be after publish date")
            except:
                pass
        return value

    def validate_target_type(self, value):
        """Validate target_type matches with provided targeting data"""
        target_user_id = self.initial_data.get('target_user_id')
        target_user_ids = self.initial_data.get('target_user_ids')
        target_customer_type = self.initial_data.get('target_customer_type')
        
        if value == 'specific_user' and not target_user_id:
            raise serializers.ValidationError("target_user_id required for specific_user targeting")
        
        if value == 'user_group' and not target_user_ids:
            raise serializers.ValidationError("target_user_ids required for user_group targeting")
        
        if value == 'customer_segment' and not target_customer_type:
            raise serializers.ValidationError("target_customer_type required for customer_segment targeting")
        
        return value

    def validate_target_user_id(self, value):
        """Validate target user exists"""
        if value:
            try:
                CustomUser.objects.get(id=value)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("Target user does not exist")
        return value

    def validate_target_user_ids(self, value):
        """Validate all target users exist"""
        if value:
            existing_users = CustomUser.objects.filter(id__in=value).count()
            if existing_users != len(value):
                raise serializers.ValidationError("One or more target users do not exist")
        return value

    def create(self, validated_data):
        # Handle target user assignments
        target_user_id = validated_data.pop('target_user_id', None)
        target_user_ids = validated_data.pop('target_user_ids', [])
        
        # Set target_user if specific user targeting
        if target_user_id:
            validated_data['target_user'] = CustomUser.objects.get(id=target_user_id)
        
        # Create the news item
        news_item = NewsItem.objects.create(**validated_data)
        
        # Set target_users for group targeting
        if target_user_ids:
            target_users = CustomUser.objects.filter(id__in=target_user_ids)
            news_item.target_users.set(target_users)
        
        return news_item

    def to_representation(self, instance):
        """Return the created news item in admin list format"""
        from .serializers import NewsItemAdminSerializer
        return NewsItemAdminSerializer(instance).data



class NewsItemDetailSerializer(serializers.ModelSerializer):
    # Map fields to match frontend structure
    publishedAt = serializers.DateTimeField(source='published_at', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    expiresAt = serializers.DateTimeField(source='expires_at', allow_null=True)
    imageUrl = serializers.URLField(source='image_url', allow_null=True)
    isPublic = serializers.BooleanField(source='is_public')
    
    # Target user information
    targetUserId = serializers.SerializerMethodField()
    targetUserEmail = serializers.SerializerMethodField()
    targetUserName = serializers.SerializerMethodField()
    
    # Target users for group targeting
    targetUsers = serializers.SerializerMethodField()
    
    # Author information
    authorId = serializers.SerializerMethodField()
    
    # Status based on published_at
    status = serializers.SerializerMethodField()
    
    # Read and engagement statistics
    readCount = serializers.SerializerMethodField()
    clickCount = serializers.IntegerField(source='click_count')
    
    # Action button as JSON
    actionButton = serializers.JSONField(source='action_button', allow_null=True)
    
    # Recent readers list
    recentReaders = serializers.SerializerMethodField()
    
    # Targeting information
    targetType = serializers.CharField(source='target_type')
    targetCustomerType = serializers.CharField(source='target_customer_type', allow_null=True)
    targetOrderStatus = serializers.CharField(source='target_order_status', allow_null=True)
    relatedOrderId = serializers.CharField(source='related_order_id', allow_null=True)
    autoGenerated = serializers.BooleanField(source='auto_generated')

    class Meta:
        model = NewsItem
        fields = [
            'id', 'title', 'content', 'excerpt', 'category', 'priority', 'status',
            'author', 'authorId', 'publishedAt', 'createdAt', 'updatedAt', 
            'expiresAt', 'imageUrl', 'isPublic', 'targetUserId', 'targetUserEmail',
            'targetUserName', 'targetUsers', 'tags', 'actionButton', 'readCount', 
            'clickCount', 'recentReaders', 'targetType', 'targetCustomerType',
            'targetOrderStatus', 'relatedOrderId', 'autoGenerated'
        ]

    def get_targetUserId(self, obj):
        return str(obj.target_user.id) if obj.target_user else None

    def get_targetUserEmail(self, obj):
        return obj.target_user.email if obj.target_user else None

    def get_targetUserName(self, obj):
        if obj.target_user:
            full_name = f"{obj.target_user.first_name} {obj.target_user.last_name}".strip()
            return full_name or obj.target_user.username
        return None

    def get_targetUsers(self, obj):
        """Get list of targeted users for group targeting"""
        if obj.target_type == 'user_group':
            users = obj.target_users.all()[:20]  # Limit to 20 for performance
            return [
                {
                    'id': str(user.id),
                    'username': user.username,
                    'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email
                }
                for user in users
            ]
        return []

    def get_authorId(self, obj):
        # Generate author ID from author name
        if obj.author:
            return obj.author.lower().replace(' ', '_').replace('team', 'team_1')
        return 'admin_1'

    def get_status(self, obj):
        if not obj.published_at:
            return 'draft'
        elif obj.published_at <= timezone.now():
            # Check if expired
            if obj.expires_at and obj.expires_at <= timezone.now():
                return 'expired'
            return 'published'
        else:
            return 'scheduled'

    def get_readCount(self, obj):
        return obj.read_by.count()

    def get_recentReaders(self, obj):
        """Get list of recent readers with timestamps"""
        recent_reads = NewsReadTracker.objects.filter(
            news_item=obj
        ).select_related('user').order_by('-read_at')[:10]
        
        return [
            {
                'id': str(read.user.id),
                'username': read.user.username,
                'full_name': f"{read.user.first_name} {read.user.last_name}".strip() or read.user.username,
                'email': read.user.email,
                'read_at': read.read_at.isoformat()
            }
            for read in recent_reads
        ]



class NewsItemUpdateSerializer(serializers.ModelSerializer):
    # Optional fields for targeting
    target_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = NewsItem
        fields = [
            'title', 'content', 'excerpt', 'category', 'priority', 'author',
            'published_at', 'expires_at', 'image_url', 'is_public',
            'target_type', 'target_user_id', 'target_user_ids',
            'target_customer_type', 'target_order_status', 
            'tags', 'action_button', 'related_order_id'
        ]

    def validate_published_at(self, value):
        """Validate published_at"""
        if value and value < timezone.now():
            # Allow past dates for immediate publishing
            pass
        return value

    def validate_expires_at(self, value):
        """Validate expires_at is after published_at"""
        published_at = self.initial_data.get('published_at')
        if value and published_at:
            try:
                pub_date = serializers.DateTimeField().to_internal_value(published_at)
                if value <= pub_date:
                    raise serializers.ValidationError("Expiry date must be after publish date")
            except:
                pass
        return value

    def validate_target_type(self, value):
        """Validate target_type matches with provided targeting data"""
        target_user_id = self.initial_data.get('target_user_id')
        target_user_ids = self.initial_data.get('target_user_ids')
        target_customer_type = self.initial_data.get('target_customer_type')
        
        if value == 'specific_user' and not target_user_id:
            raise serializers.ValidationError("target_user_id required for specific_user targeting")
        
        if value == 'user_group' and not target_user_ids:
            raise serializers.ValidationError("target_user_ids required for user_group targeting")
        
        if value == 'customer_segment' and not target_customer_type:
            raise serializers.ValidationError("target_customer_type required for customer_segment targeting")
        
        return value

    def validate_target_user_id(self, value):
        """Validate target user exists"""
        if value:
            try:
                CustomUser.objects.get(id=value)
            except CustomUser.DoesNotExist:
                raise serializers.ValidationError("Target user does not exist")
        return value

    def validate_target_user_ids(self, value):
        """Validate all target users exist"""
        if value:
            existing_users = CustomUser.objects.filter(id__in=value).count()
            if existing_users != len(value):
                raise serializers.ValidationError("One or more target users do not exist")
        return value

    def update(self, instance, validated_data):
        # Handle target user assignments
        target_user_id = validated_data.pop('target_user_id', None)
        target_user_ids = validated_data.pop('target_user_ids', [])
        
        # Clear existing target_user if not specific_user targeting
        if validated_data.get('target_type') != 'specific_user':
            validated_data['target_user'] = None
        elif target_user_id:
            validated_data['target_user'] = CustomUser.objects.get(id=target_user_id)
        
        # Update all fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        
        # Handle target_users for group targeting
        if validated_data.get('target_type') == 'user_group' and target_user_ids:
            target_users = CustomUser.objects.filter(id__in=target_user_ids)
            instance.target_users.set(target_users)
        else:
            # Clear target_users if not group targeting
            instance.target_users.clear()
        
        return instance

    def to_representation(self, instance):
        """Return the updated news item in admin detail format"""
        from .serializers import NewsItemDetailSerializer
        return NewsItemDetailSerializer(instance).data