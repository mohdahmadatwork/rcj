from rest_framework import serializers
from .models import Category, WorkSample


class CategorySerializer(serializers.ModelSerializer):
    """Serializer for Category model"""
    work_samples_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'work_samples_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkSampleListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing work samples"""
    category = serializers.StringRelatedField()
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkSample
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'category_slug',
            'image_url', 'image_alt_text', 'is_featured', 'display_order','is_active'
        ]

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class WorkSampleDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for individual work sample"""
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkSample
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'category_id',
            'image', 'image_url', 'image_alt_text', 'is_featured', 'is_active',
            'display_order', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            if request is not None:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class WorkSampleCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating work samples"""
    
    class Meta:
        model = WorkSample
        fields = [
            'title', 'slug', 'description', 'category', 'image',
            'image_alt_text', 'is_featured', 'is_active', 'display_order'
        ]

    def validate_image(self, value):
        """Validate image file size (max 5MB)"""
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Image file size cannot exceed 5MB.")
        return value
