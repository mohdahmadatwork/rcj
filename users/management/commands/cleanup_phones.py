from django.core.management.base import BaseManagementCommand
from users.models import CustomUser

class Command(BaseManagementCommand):
    help = 'Cleans up empty phone numbers by setting them to NULL'

    def handle(self, *args, **options):
        # 1. Handle empty strings
        self.stdout.write('Cleaning up empty phone numbers...')
        count = CustomUser.objects.filter(phone='').update(phone=None)
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} users with empty phone strings to NULL.'))

        # 2. Handle actual duplicates
        self.stdout.write('Checking for duplicate phone numbers...')
        from django.db.models import Count
        
        # Find phone numbers that appear more than once (excluding None)
        duplicates = CustomUser.objects.values('phone').exclude(phone=None).annotate(count=Count('id')).filter(count__gt=1)
        
        dup_count = 0
        for entry in duplicates:
            phone_val = entry['phone']
            # Get all users with this phone, ordered by join date (most recent first)
            users_with_dup = CustomUser.objects.filter(phone=phone_val).order_by('-date_joined')
            
            # Keep the phone for the first user (most recent), clear for others
            # We assume the most recent account is the valid one.
            for user in users_with_dup[1:]:
                user.phone = None
                user.save(update_fields=['phone'])
                self.stdout.write(f"  - Removed duplicate phone '{phone_val}' from user '{user.username}' (ID: {user.id})")
                dup_count += 1

        if dup_count > 0:
            self.stdout.write(self.style.WARNING(f'Resolved {dup_count} duplicate phone conflicts by setting older accounts to NULL.'))
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate phone numbers found.'))
