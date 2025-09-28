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

        # Generate unique username
        first = (data.get("given_name") or "").strip().lower()
        last = (data.get("family_name") or "").strip().lower() or ""
        suffix = random.randint(1000, 9999)
        username = f"{first}.{last}.{suffix}".replace(" ", "")
        user.username   = username
        user.first_name = first.capitalize()
        user.last_name  = last.capitalize()
        user.email      = data.get("email", "")
        return user
