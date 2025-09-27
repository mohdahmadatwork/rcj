# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
from datetime import datetime

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('customer', 'Customer'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='customer')
    phone = models.CharField(max_length=15, blank=True)
    client_id = models.CharField(max_length=20, unique=True, blank=True, null=True)
    
    def save(self, *args, **kwargs):
        # Generate client_id for customers if not exists
        if not self.client_id and self.user_type == 'customer':
            self.client_id = f"CLI{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}"
        super().save(*args, **kwargs)
    
    def is_admin_user(self):
        return self.user_type == 'admin'
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
