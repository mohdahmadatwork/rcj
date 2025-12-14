import os
import django
from django.db.models import Count

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jewelry_orders.settings')
django.setup()

from users.models import CustomUser

# Check for non-empty duplicates
duplicates = CustomUser.objects.values('phone').annotate(count=Count('phone')).filter(count__gt=1).exclude(phone='')
print("Duplicate Phones (non-empty):")
for d in duplicates:
    print(f"Phone: '{d['phone']}' - Count: {d['count']}")

# Check for empty string duplicates
empty_count = CustomUser.objects.filter(phone='').count()
print(f"\nUsers with empty phone string: {empty_count}")

# Check for None duplicates
none_count = CustomUser.objects.filter(phone__isnull=True).count()
print(f"Users with None phone: {none_count}")
