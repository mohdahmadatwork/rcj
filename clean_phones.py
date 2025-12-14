from users.models import CustomUser

# Update empty strings to None
updated_count = CustomUser.objects.filter(phone='').update(phone=None)
print(f"Updated {updated_count} users with empty phone string to None.")
