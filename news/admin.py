from django.contrib import admin
from .models import NewsItem

@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'priority', 'author',
        'published_at', 'expires_at', 'is_public', 'target_user'
    ]
    list_filter = ['category', 'priority', 'is_public', 'published_at']
    search_fields = ['title', 'content', 'tags']
    readonly_fields = ['id']
    fieldsets = (
        (None, {
            'fields': ('title', 'content', 'excerpt', 'image_url', 'action_button')
        }),
        ('Meta', {
            'fields': ('category', 'priority', 'author', 'tags')
        }),
        ('Visibility', {
            'fields': ('is_public', 'target_user', 'published_at', 'expires_at')
        }),
    )
