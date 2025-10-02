# news/serializers.py
from rest_framework import serializers
from .models import NewsItem

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
