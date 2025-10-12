# news/serializers.py

import os
import uuid
from rest_framework import serializers
from django.utils import timezone
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import NewsItem, NewsReadTracker
from users.models import CustomUser




def build_full_image_url(image_url, request=None):
    """
    Smart image URL handler:
    - If URL starts with http:// or https://, return as-is (external URL)
    - Otherwise, build full URL with base domain (uploaded file)
    """
    if not image_url:
        return None
        
    # Check if it's already a full URL (external image)
    if image_url.startswith(('http://', 'https://')):
        return image_url
    
    # Build full URL for uploaded files or relative paths
    if request:
        if image_url.startswith('/'):
            return request.build_absolute_uri(image_url)
        
        if not image_url.startswith('/'):
            base_url = request.build_absolute_uri('/')[:-1]
            return f"{base_url}/{image_url}"
    
    return image_url


class NewsItemListSerializer(serializers.ModelSerializer):
    """Serializer for news list view - public API"""
    isRead = serializers.SerializerMethodField()
    isPublic = serializers.BooleanField(source='is_public', read_only=True)
    imageUrl = serializers.SerializerMethodField()
    publishedAt = serializers.CharField(source='published_at', read_only=True)
    expiresAt = serializers.CharField(source='expires_at', read_only=True)
    actionButton = serializers.JSONField(source='action_button', read_only=True)

    class Meta:
        model = NewsItem
        fields = [
            'id', 'title', 'excerpt', 'category', 'priority', 'author',
            'publishedAt', 'expiresAt', 'imageUrl', 'isPublic',
            'target_user', 'isRead', 'tags', 'actionButton'
        ]

    def get_isRead(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return obj.read_by.filter(id=user.id).exists()
    def get_imageUrl(self, obj):
        return build_full_image_url(obj.image_url, self.context.get('request'))



class NewsItemDetailSerializer(serializers.ModelSerializer):
    """Serializer for news detail view - public API"""
    is_read = serializers.SerializerMethodField()
    target_user_id = serializers.PrimaryKeyRelatedField(
        source='target_user', read_only=True
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = NewsItem
        fields = [
            'id', 'title', 'content', 'excerpt', 'category', 'priority', 'author',
            'published_at', 'expires_at', 'image_url', 'is_public', 'target_user_id',
            'is_read', 'tags', 'action_button'
        ]

    def get_is_read(self, obj):
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return obj.read_by.filter(id=user.id).exists()
    def get_image_url(self, obj):
        return build_full_image_url(obj.image_url, self.context.get('request'))


class NewsItemAdminSerializer(serializers.ModelSerializer):
    """Serializer for admin news list view"""
    # Map fields to match frontend structure
    publishedAt = serializers.DateTimeField(source='published_at', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    expiresAt = serializers.DateTimeField(source='expires_at', allow_null=True)
    imageUrl = serializers.SerializerMethodField()
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
    clickCount = serializers.IntegerField(source='click_count')

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
            # Check if expired
            if obj.expires_at and obj.expires_at <= timezone.now():
                return 'expired'
            return 'published'
        else:
            return 'scheduled'

    def get_readCount(self, obj):
        return obj.read_by.count()
    def get_imageUrl(self, obj):
        return build_full_image_url(obj.image_url, self.context.get('request'))


class NewsItemCreateSerializerAdmin(serializers.ModelSerializer):
    """Updated serializer for creating news items with file upload support"""
    # Optional fields for targeting
    target_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    # Change from URLField to ImageField for file upload
    image = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = NewsItem
        fields = [
            'title', 'content', 'excerpt', 'category', 'priority', 'author',
            'published_at', 'expires_at', 'image', 'is_public',  # Changed from 'image_url' to 'image'
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
    
    def _handle_image_upload(self, image_file):
        """Handle image upload and return the URL"""
        if not image_file:
            return None
            
        # Generate unique filename
        file_extension = os.path.splitext(image_file.name)[1]
        unique_filename = f"news/{uuid.uuid4()}{file_extension}"
        
        # Save the file
        file_path = default_storage.save(unique_filename, ContentFile(image_file.read()))
        
        # Return the full URL
        if hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL:
            return f"{settings.MEDIA_URL}{file_path}"
        else:
            # Fallback to relative path if MEDIA_URL not configured
            return f"/media/{file_path}"

    def create(self, validated_data):
        # Handle image upload
        image_file = validated_data.pop('image', None)
        if image_file:
            validated_data['image_url'] = self._handle_image_upload(image_file)
        
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
        return NewsItemAdminSerializer(instance).data


class NewsItemAdminDetailSerializer(serializers.ModelSerializer):
    """Extended serializer for admin news detail view with comprehensive information"""
    # Map fields to match frontend structure
    publishedAt = serializers.DateTimeField(source='published_at', allow_null=True)
    createdAt = serializers.DateTimeField(source='created_at')
    updatedAt = serializers.DateTimeField(source='updated_at')
    expiresAt = serializers.DateTimeField(source='expires_at', allow_null=True)
    imageUrl = serializers.SerializerMethodField()
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
    def get_imageUrl(self, obj):
        return build_full_image_url(obj.image_url, self.context.get('request'))



class NewsItemUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating news items"""
    # Optional fields for targeting
    target_user_id = serializers.IntegerField(required=False, allow_null=True)
    target_user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    # Support both image file upload and URL
    image = serializers.ImageField(required=False, allow_null=True, write_only=True)
    image_url = serializers.URLField(required=False, allow_null=True)

    class Meta:
        model = NewsItem
        fields = [
            'title', 'content', 'excerpt', 'category', 'priority', 'author',
            'published_at', 'expires_at', 'image', 'image_url', 'is_public',
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

    def validate(self, data):
        """Cross-field validation"""
        image = data.get('image')
        image_url = data.get('image_url')
        
        # Don't allow both image file and URL
        if image and image_url:
            raise serializers.ValidationError("Cannot provide both image file and image URL")
        
        return data
    
    def _handle_image_upload(self, image_file):
        """Handle image upload and return the URL"""
        if not image_file:
            return None
            
        # Generate unique filename
        file_extension = os.path.splitext(image_file.name)[1]
        unique_filename = f"news/{uuid.uuid4()}{file_extension}"
        
        # Save the file
        file_path = default_storage.save(unique_filename, ContentFile(image_file.read()))
        
        # Return the full URL
        if hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL:
            return f"{settings.MEDIA_URL}{file_path}"
        else:
            return f"/media/{file_path}"

    def update(self, instance, validated_data):
        # Handle image upload if provided
        image_file = validated_data.pop('image', None)
        if image_file:
            # Remove existing image_url if provided in data
            validated_data.pop('image_url', None)
            validated_data['image_url'] = self._handle_image_upload(image_file)
        
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
        return NewsItemAdminDetailSerializer(instance).data


# Legacy alias for backward compatibility
NewsItemDetailSerializer = NewsItemAdminDetailSerializer


# news/utils.py
