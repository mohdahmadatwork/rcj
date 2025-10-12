from django.contrib import admin
from .models import NewsItem, NewsImage, NewsReadTracker

@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = [
        'title','category','priority','author',
        'published_at','expires_at','is_public',
        'target_type','target_user','auto_generated','click_count',
        'status_display'
    ]
    list_filter = [
        'category','priority','is_public','target_type',
        'target_customer_type','target_order_status','auto_generated'
    ]
    search_fields = ['title','content','tags']
    ordering = ['-published_at']

    readonly_fields = [
        'id','created_at','updated_at',
        'status_display','get_primary_image_url','read_count'
    ]

    fieldsets = (
        (None, {
            'fields': (
                'title','content','excerpt','image_url','action_button',
                'get_primary_image_url'
            )
        }),
        ('Metadata', {
            'fields': (
                'category','priority','author','tags',
                'related_order_id','auto_generated'
            )
        }),
        ('Visibility & Scheduling', {
            'fields': (
                'is_public','target_type','target_user','target_users',
                'target_customer_type','target_order_status',
                'published_at','expires_at','status_display'
            )
        }),
        ('Analytics & Tracking', {
            'fields': (
                'click_count','read_count',
                'created_at','updated_at'
            )
        }),
    )

    @admin.display(description='Status')
    def status_display(self, obj):
        return obj.get_status()

    @admin.display(description='Primary Image URL')
    def get_primary_image_url(self, obj):
        url = obj.get_primary_image_url()
        return url or '—'

    @admin.display(description='Read Count')
    def read_count(self, obj):
        return obj.read_by.count()
    

@admin.register(NewsImage)
class NewsImageAdmin(admin.ModelAdmin):
    list_display = ['id', 'news_item', 'is_primary', 'uploaded_at']
    list_filter = ['is_primary']
    search_fields = ['news_item__title', 'alt_text']
    readonly_fields = ['id', 'uploaded_at']
    ordering = ['-uploaded_at']


@admin.register(NewsReadTracker)
class NewsReadTrackerAdmin(admin.ModelAdmin):
    list_display = ['user', 'news_item', 'read_at']
    list_filter = ['read_at']
    search_fields = ['user__username', 'news_item__title']
    readonly_fields = ['user', 'news_item', 'read_at']
    ordering = ['-read_at']
