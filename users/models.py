# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    USER_TYPES = (
        ('admin', 'Admin'),
        ('normal', 'Normal User'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPES, default='normal')
    phone = models.CharField(max_length=15, blank=True)
    
    def is_admin_user(self):
        return self.user_type == 'admin'
