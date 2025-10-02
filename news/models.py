# news/models.py
import uuid
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class NewsItem(models.Model):
    CATEGORY_CHOICES = [
        ('announcement','Announcement'),('sale','Sale'),
        ('promotion','Promotion'),('update','Update'),
        ('event','Event'),('personal','Personal'),
    ]
    PRIORITY_CHOICES = [('high','High'),('medium','Medium'),('low','Low')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    content = models.TextField()
    excerpt = models.CharField(max_length=500)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    author = models.CharField(max_length=100)
    published_at = models.DateTimeField()
    expires_at = models.DateTimeField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    is_public = models.BooleanField(default=True)
    target_user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    tags = models.JSONField(default=list)  # list of strings
    action_button = models.JSONField(null=True, blank=True)
    read_by = models.ManyToManyField(User, blank=True, related_name='read_news_items')
    class Meta:
        ordering = ['-published_at']
