# orders/admin.py
from django.contrib import admin
from .models import Order, OrderFile, OrderLog

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
            'fields': ('full_name', 'contact_number', 'email', 'address')
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
