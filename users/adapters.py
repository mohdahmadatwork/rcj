# users/adapters.py
import random
from django.contrib.auth import get_user_model
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialAccount

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # Link to existing user by email
        email = sociallogin.account.extra_data.get("email")
        if not email:
            return

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        # If SocialAccount already exists, do nothing
        if SocialAccount.objects.filter(user=user, provider=sociallogin.account.provider).exists():
            return

        # Link and login
        sociallogin.connect(request, user)

    def populate_user(self, request, sociallogin, data):
        # Called only for new users
        user = super().populate_user(request, sociallogin, data)

         # Get data from extra_data first, then fallback to data parameter
        extra_data = sociallogin.account.extra_data
        
        # Google payload fields - check extra_data first
        full_name   = extra_data.get("name") or data.get("name") or ""
        given_name  = extra_data.get("given_name") or data.get("given_name") or ""
        family_name = extra_data.get("family_name") or data.get("family_name") or ""

        # If no family_name, try splitting full_name
        if not family_name and full_name:
            parts = full_name.strip().split()
            if len(parts) > 1:
                given_name  = parts[0]
                family_name = parts[-1]

        # Clean and lowercase
        first = given_name.strip().lower() or "user"
        last  = family_name.strip().lower() or "anon"

        # Generate a random 4-digit suffix
        suffix = random.randint(1000, 9999)
        username = f"{first}.{last}.{suffix}".replace(" ", "")
        user.username   = username
        user.first_name = first.capitalize()
        user.last_name  = last.capitalize()
        user.email      = data.get("email", "")
        return user
