# orders/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid
from datetime import datetime
from django.contrib.auth import get_user_model

User = get_user_model()

class Order(models.Model):
    ORDER_STATUS_CHOICES = [
        ('declined', 'Declined'),
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('cad_done', 'CAD Done'),
        ('user_confirmed', 'User Approved'),
        ('rpt_done', 'RPT Done'),
        ('casting', 'Casting'),
        ('ready', 'Ready'),
        ('delivered', 'Delivered'),
    ]
    
    order_id = models.CharField(max_length=20, unique=True, editable=False)
    client_id = models.CharField(max_length=20)  # This will be user's client_id
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders',default=1)  # New field
    full_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20)
    email = models.EmailField()
    description = models.TextField()
    special_requirements = models.TextField(blank=True, null=True)
    diamond_size = models.CharField(max_length=100, blank=True, null=True)
    gold_weight = models.CharField(max_length=100, blank=True, null=True)
    gold_color = models.CharField(max_length=200, blank=True, null=True)
    preferred_delivery_date = models.DateField()
    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='new')
    declined_reason = models.TextField(blank=True, null=True)
    declined_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='declined_orders')
    declined_at = models.DateTimeField(auto_now=True, null=True, blank=True) 
    estimated_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    address = models.TextField(default='',null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_orders')
    
    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
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
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='order_file_responses')
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


class Message(models.Model):
    SENDER_TYPE_CHOICES = [
        ('user', 'User'),
        ('admin', 'Admin'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender_type = models.CharField(max_length=10, choices=SENDER_TYPE_CHOICES)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    
    # Optional order relationship
    order = models.ForeignKey('Order', on_delete=models.CASCADE, null=True, blank=True, related_name='messages')
    
    # Message content
    text = models.TextField()
    
    # Metadata
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For system messages
    is_system_message = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        # Auto-set sender_type based on user role
        if not self.sender_type:
            if self.is_system_message:
                self.sender_type = 'system'
            elif self.sender.is_staff or self.sender.is_superuser:
                self.sender_type = 'admin'
            else:
                self.sender_type = 'user'
        super().save(*args, **kwargs)

    def __str__(self):
        order_info = f" (Order: {self.order.order_id})" if self.order else ""
        return f"{self.sender_type.title()} message{order_info} - {self.text[:50]}..."


class Contact(models.Model):
    CONTACT_METHOD_CHOICES = [
        ('email', 'Email'),
        ('phone', 'Phone'),
        ('either', 'Either'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # User information
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # Contact details
    subject = models.CharField(max_length=200)
    message = models.TextField()
    preferred_contact_method = models.CharField(max_length=10, choices=CONTACT_METHOD_CHOICES)
    
    # Order related
    order_related = models.BooleanField(default=False)
    order_id = models.CharField(max_length=50, blank=True, null=True)
    related_order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Admin response
    admin_response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='contact_responses')

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generate ticket number like CT202510020001
            from django.utils import timezone
            today = timezone.now()
            date_str = today.strftime('%Y%m%d')
            
            # Get the last ticket number for today
            last_contact = Contact.objects.filter(
                ticket_number__startswith=f'CT{date_str}'
            ).order_by('-ticket_number').first()
            
            if last_contact:
                last_num = int(last_contact.ticket_number[-4:])
                next_num = last_num + 1
            else:
                next_num = 1
                
            self.ticket_number = f'CT{date_str}{next_num:04d}'
        
        # Link to related order if order_id is provided
        if self.order_id and not self.related_order:
            try:
                self.related_order = Order.objects.get(order_id=self.order_id)
            except Order.DoesNotExist:
                pass
                
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.ticket_number} - {self.subject}'
