# orders/admin.py
from django.contrib import admin
from .models import Order, OrderFile, OrderLog, Contact
from django.core.management import call_command
from django.contrib import messages

@admin.action(description='Create backup of today\'s data')
def create_backup_action(modeladmin, request, queryset):
    try:
        call_command('backup_daily_data')
        messages.success(request, 'Backup created successfully!')
    except Exception as e:
        messages.error(request, f'Backup failed: {str(e)}')



class OrderFileInline(admin.TabularInline):
    model = OrderFile
    extra = 0
    readonly_fields = ['uploaded_at']

class OrderLogInline(admin.TabularInline):
    model = OrderLog
    extra = 0
    readonly_fields = ['timestamp', 'user', 'action', 'changes']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'order_id', 'client_id', 'full_name', 'contact_number', 
        'order_status', 'created_at', 'preferred_delivery_date'
    ]
    list_filter = ['order_status', 'created_at', 'preferred_delivery_date']
    search_fields = ['order_id', 'client_id', 'full_name', 'email', 'contact_number']
    readonly_fields = ['order_id', 'client_id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_id', 'client_id', 'order_status', 'declined_reason')
        }),
        ('Customer Details', {
            'fields': ('customer','full_name', 'contact_number', 'email', 'address')
        }),
        ('Order Details', {
            'fields': ('description', 'special_requirements', 'diamond_size', 
                      'gold_weight', 'estimated_value', 'preferred_delivery_date')
        }),
        ('System Info', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [OrderFileInline, OrderLogInline]

    actions = [create_backup_action]

    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(OrderFile)
class OrderFileAdmin(admin.ModelAdmin):
    list_display = ['order', 'file_type', 'stage', 'caption', 'uploaded_at']
    list_filter = ['file_type', 'stage', 'uploaded_at']
    search_fields = ['order__order_id', 'caption']
    readonly_fields = ['uploaded_at']

@admin.register(OrderLog)
class OrderLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'user', 'action', 'timestamp']
    list_filter = ['timestamp', 'user']
    search_fields = ['order__order_id', 'action', 'user__username']
    readonly_fields = ['timestamp']
    
    def has_add_permission(self, request):
        return False  # Prevent manual creation of logs
    
    def has_change_permission(self, request, obj=None):
        return False  # Prevent editing of logs


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = [
        'ticket_number', 'full_name', 'email', 'subject', 
        'status', 'order_related', 'created_at'
    ]
    list_filter = [
        'status', 'order_related', 'preferred_contact_method', 
        'created_at'
    ]
    search_fields = [
        'ticket_number', 'full_name', 'email', 'subject', 
        'order_id'
    ]
    readonly_fields = ['id', 'ticket_number', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('ticket_number', 'user', 'full_name', 'email', 'phone')
        }),
        ('Request Details', {
            'fields': ('subject', 'message', 'preferred_contact_method')
        }),
        ('Order Related', {
            'fields': ('order_related', 'order_id', 'related_order')
        }),
        ('Status & Response', {
            'fields': ('status', 'admin_response', 'responded_by', 'responded_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


from django.contrib import admin
from django.utils.html import format_html
from .models import Message

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'sender_type_badge', 'sender', 'order_link', 'text_preview', 'is_read', 'read_status', 'created_at']
    list_filter = ['sender_type', 'is_read', 'is_system_message', 'created_at']
    search_fields = ['text', 'sender__username', 'sender__email', 'order__order_id']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_editable = ['is_read']
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Message Information', {
            'fields': ('id', 'sender_type', 'sender', 'order')
        }),
        ('Content', {
            'fields': ('text', 'is_system_message')
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Custom colored badge for sender type
    def sender_type_badge(self, obj):
        colors = {
            'user': '#3498db',
            'admin': '#e74c3c',
            'system': '#95a5a6'
        }
        color = colors.get(obj.sender_type, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.sender_type.upper()
        )
    sender_type_badge.short_description = 'Sender Type'
    
    # Clickable order link
    def order_link(self, obj):
        if obj.order:
            from django.urls import reverse
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_id)
        return '-'
    order_link.short_description = 'Order'
    
    # Visual read status
    def read_status(self, obj):
        if obj.is_read:
            return format_html('<span style="color: green;">✓ Read</span>')
        return format_html('<span style="color: red;">✗ Unread</span>')
    read_status.short_description = 'Status'
    
    # Text preview
    def text_preview(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    text_preview.short_description = 'Message'
    
    # Optimize database queries
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('sender', 'order')
    
    # Custom actions
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'{updated} message(s) marked as read.')
    mark_as_read.short_description = 'Mark selected messages as read'
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'{updated} message(s) marked as unread.')
    mark_as_unread.short_description = 'Mark selected messages as unread'
