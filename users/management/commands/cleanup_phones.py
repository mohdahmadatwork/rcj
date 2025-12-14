from django.core.management.base import BaseCommand
from users.models import CustomUser

class Command(BaseCommand):
    help = 'Cleans up empty phone numbers by setting them to NULL'

    def handle(self, *args, **options):
        from django.db.utils import IntegrityError
        from django.db.models import Count
        import uuid

        self.stdout.write('Starting phone number cleanup...')

        # Step 0: Clean up previously created temporary placeholders (if schema now allows NULL)
        # This runs if the user ran the script, migrated, and is running it again.
        temp_placeholders = CustomUser.objects.filter(phone__startswith='tmp_')
        if temp_placeholders.exists():
            self.stdout.write('Found temporary placeholders. Attempting to convert to NULL...')
            try:
                updated = temp_placeholders.update(phone=None)
                self.stdout.write(self.style.SUCCESS(f'Converted {updated} temporary placeholders to NULL.'))
            except IntegrityError:
                self.stdout.write(self.style.WARNING('Schema still forbids NULL. Keeping placeholders for now.'))

        # Step 1: Handle empty strings
        empty_phones = CustomUser.objects.filter(phone='')
        if empty_phones.exists():
            self.stdout.write(f'Found {empty_phones.count()} empty phone numbers.')
            try:
                # Try setting to None (preferred)
                count = empty_phones.update(phone=None)
                self.stdout.write(self.style.SUCCESS(f'Successfully updated {count} users with empty phone strings to NULL.'))
            except IntegrityError:
                self.stdout.write(self.style.WARNING('Database schema enforces NOT NULL. Using temporary unique placeholders instead...'))
                # Fallback: Set unique temporary string to satisfy NOT NULL and UNIQUE future constraint
                count = 0
                for user in empty_phones:
                    # distinct placeholder <= 15 chars
                    user.phone = f"tmp_{user.id}"
                    user.save(update_fields=['phone'])
                    count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated {count} users to temporary placeholders (e.g., "tmp_123").'))
                self.stdout.write(self.style.WARNING('IMPORTANT: Run migrations, then RUN THIS SCRIPT AGAIN to finalize cleanup.'))

        # Step 2: Handle actual duplicates
        self.stdout.write('Checking for duplicate phone numbers...')
        
        # Determine what to exclude (None and placeholders)
        duplicates = CustomUser.objects.exclude(phone=None).exclude(phone__startswith='tmp_').values('phone').annotate(count=Count('id')).filter(count__gt=1)
        
        dup_count = 0
        for entry in duplicates:
            phone_val = entry['phone']
            users_with_dup = CustomUser.objects.filter(phone=phone_val).order_by('-date_joined')
            
            # Keep the first one, "remove" others
            for user in users_with_dup[1:]:
                try:
                    user.phone = None
                    user.save(update_fields=['phone'])
                    self.stdout.write(f"  - Removed duplicate phone '{phone_val}' from user '{user.username}' (ID: {user.id})")
                except IntegrityError:
                     # Fallback if NULL not allowed
                    user.phone = f"tmp_{user.id}"
                    user.save(update_fields=['phone'])
                    self.stdout.write(f"  - Renamed duplicate phone '{phone_val}' to '{user.phone}' for user '{user.username}'")
                dup_count += 1

        if dup_count > 0:
            self.stdout.write(self.style.SUCCESS(f'Resolved {dup_count} duplicate phone conflicts.'))
        else:
            self.stdout.write(self.style.SUCCESS('No duplicate phone numbers found.'))
