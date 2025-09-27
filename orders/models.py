# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
from auditlog.registry import auditlog
import uuid
from datetime import datetime

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('declined', 'Declined'),
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('cad_done', 'CAD Done'),
        ('rpt_done', 'RPT Done'),
        ('casting', 'Casting'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
    ]
    
    order_id = models.CharField(max_length=20, unique=True, editable=False)
    client_id = models.CharField(max_length=20, editable=False)
    full_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    description = models.TextField()
    special_requirements = models.TextField(blank=True, null=True)
    diamond_size = models.CharField(max_length=100, blank=True, null=True)
    gold_weight = models.CharField(max_length=100, blank=True, null=True)
    preferred_delivery_date = models.DateField()
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='new')
    declined_reason = models.TextField(blank=True, null=True)
    estimated_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    address = models.TextField(default='',null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        if not self.client_id:
            self.client_id = f"CLI{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Order {self.order_id} - {self.full_name}"

class OrderFile(models.Model):
    STAGE_CHOICES = [
        ('initial', 'Initial Upload'),
        ('cad_done', 'CAD Stage'),
        ('rpt_done', 'RPT Stage'),
        ('casting', 'Casting Stage'),
        ('ready', 'Ready Stage'),
    ]
    
    order = models.ForeignKey(Order, related_name='files', on_delete=models.CASCADE)
    file = models.FileField(upload_to='order_files/')
    file_type = models.CharField(max_length=20, choices=[('image', 'Image'), ('video', 'Video')])
    caption = models.CharField(max_length=255, blank=True)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='initial')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.order.order_id} - {self.file.name}"

class OrderLog(models.Model):
    order = models.ForeignKey(Order, related_name='logs', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    changes = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.order.order_id} - {self.action} by {self.user}"

# Register models for audit logging
auditlog.register(Order)
auditlog.register(OrderFile)
