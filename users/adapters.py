# users/adapters.py
import random
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Called before saving a newly signed-up social user.
        """
        user = super().populate_user(request, sociallogin, data)
        
        # Extract first and last name from data
        first = data.get('given_name') or user.first_name or ''
        last = data.get('family_name') or user.last_name or ''
        
        # Clean and lowercase
        first = first.strip().lower()
        last = last.strip().lower()
        
        # Generate a random 4-digit suffix
        suffix = random.randint(1000, 9999)
        
        # Build username; ensure no spaces or special chars
        username = f"{first}.{last}.{suffix}"
        username = username.replace(' ', '')
        
        user.username = username
        
        # Set names and email if not already set
        user.first_name = first.capitalize()
        user.last_name = last.capitalize()
        user.email = data.get('email', '')
        
        return user
