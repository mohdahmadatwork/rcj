# users/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.authtoken.models import Token
from dj_rest_auth.registration.serializers import RegisterSerializer
# from rest_framework import serializers
# from django.contrib.auth import get_user_model
# from dj_rest_auth.registration.views import SocialLoginView
# from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
# from allauth.socialaccount.providers.oauth2.client import OAuth2Client

User = get_user_model()

class UserDetailSerializer(serializers.ModelSerializer):
    """Serializer for user details in login response"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'phone', 'user_type']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'phone', 'first_name', 'last_name']
    
    def validate_phone(self, value):
        if not value:
            return value
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        validated_data['user_type'] = 'customer'
        user = User.objects.create_user(**validated_data)
        Token.objects.get_or_create(user=user)
        return user

class CustomRegisterSerializer(RegisterSerializer):
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate_phone(self, value):
        if not value:
            return value
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value
    
    def custom_signup(self, request, user):
        user.first_name = self.validated_data.get('first_name', '')
        user.last_name = self.validated_data.get('last_name', '')
        user.phone = self.validated_data.get('phone', '')
        user.user_type = 'customer'
        user.save(update_fields=['first_name', 'last_name', 'phone', 'user_type'])

# Update the UserLoginSerializer to include deactivation details
class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        
        if username and password:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                raise serializers.ValidationError('Invalid username or password.')

            # user = authenticate(username=username, password=password)
            print(user)
            print(f"is_active: {user.is_active}")
            print(f"deactivation_reason: {user.deactivation_reason}")
            print(f"reactivation_instructions: {user.reactivation_instructions}")
            print(f"deactivated_at: {user.deactivated_at}")
            if user.check_password(password):
                if user.is_active:
                    data['user'] = user
                    return data
                else:
                    # User account is disabled - provide detailed reason
                    error_detail = {
                        'message': 'Your account has been deactivated by the administrator.',
                        'deactivation_reason': user.deactivation_reason or 'No reason provided',
                        'reactivation_instructions': user.reactivation_instructions or 'Please contact support for assistance.',
                        'deactivated_at': user.deactivated_at,
                        'contact_support': True
                    }
                    raise serializers.ValidationError(error_detail)
            else:
                raise serializers.ValidationError('Invalid username or password.')
        else:
            raise serializers.ValidationError('Must include username and password.')

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'client_id']
        read_only_fields = ['username', 'client_id']

class CustomerListSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    phone = serializers.CharField(read_only=True)
    client_id = serializers.CharField(read_only=True)
    date_joined = serializers.DateTimeField(read_only=True)
    last_login = serializers.DateTimeField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    orders_count = serializers.SerializerMethodField()
    # total_order_value = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'email', 'phone', 'client_id',
            'date_joined', 'last_login', 'is_active', 'orders_count'
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_orders_count(self, obj):
        # Assuming you have Order model with customer foreign key
        if hasattr(obj, 'orders'):
            return obj.orders.count()
        return 0

    # def get_total_order_value(self, obj):
    #     # Calculate total order value for the customer
    #     if hasattr(obj, 'orders'):
    #         total = sum(order.final_price or order.estimated_price or 0 for order in obj.orders.all())
    #         return float(total)
    #     return 0.0


class CustomerLookupSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'client_id', 'email']

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username
    

# users/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'}, label='Confirm Password')
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'password2', 'first_name', 'last_name', 'user_type', 'phone', 'client_id']
        read_only_fields = ['id', 'client_id']
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_phone(self, value):
        if not value:
            return value
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits.")
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits.")
        return value
    
    def validate(self, attrs):
        # Validate that passwords match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        if attrs['user_type'] == 'admin':
            raise serializers.ValidationError({"user_type": "User Type can not be admin"})
        return attrs
    
    def create(self, validated_data):
        # Remove password2 as it's not needed for user creation
        validated_data.pop('password2')
        
        # Use create_user method to properly hash the password
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            user_type=validated_data.get('user_type', 'customer'),
            phone=validated_data.get('phone', ''),
        )
        
        return user


# Add this to the existing UserSerializer class
class UserSerializer(serializers.ModelSerializer):
    """Serializer for listing/retrieving users (without password)"""
    deactivated_by_username = serializers.CharField(source='deactivated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'user_type', 'phone', 'client_id', 'is_active', 'date_joined',
            'deactivation_reason', 'reactivation_instructions', 
            'deactivated_at', 'deactivated_by_username'
        ]
        read_only_fields = ['id', 'client_id', 'date_joined', 'deactivated_at', 'deactivated_by_username']


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users"""
    deactivated_by_username = serializers.CharField(source='deactivated_by.username', read_only=True, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'user_type',
            'phone',
            'client_id',
            'is_active',
            'date_joined',
            'deactivation_reason',
            'reactivation_instructions',
            'deactivated_at',
            'deactivated_by_username'
        ]
        read_only_fields = fields


class UserStatsSerializer(serializers.Serializer):
    """Serializer for user statistics"""
    total_users = serializers.IntegerField()
    admin_users = serializers.IntegerField()
    customers = serializers.IntegerField()
    inactive_users = serializers.IntegerField()


class UserStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user active status with reason"""
    
    class Meta:
        model = User
        fields = ['is_active', 'deactivation_reason', 'reactivation_instructions']
    
    def validate(self, attrs):
        # If deactivating user (is_active = False), require reason and instructions
        if not attrs.get('is_active', True):
            if not attrs.get('deactivation_reason'):
                raise serializers.ValidationError({
                    "deactivation_reason": "Deactivation reason is required when deactivating a user."
                })
            if not attrs.get('reactivation_instructions'):
                raise serializers.ValidationError({
                    "reactivation_instructions": "Reactivation instructions are required when deactivating a user."
                })
        return attrs
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        is_active = validated_data.get('is_active', instance.is_active)
        
        if not is_active and instance.is_active:
            # User is being deactivated
            instance.deactivation_reason = validated_data.get('deactivation_reason')
            instance.reactivation_instructions = validated_data.get('reactivation_instructions')
            instance.deactivated_at = datetime.now()
            if request and request.user:
                instance.deactivated_by = request.user
        elif is_active and not instance.is_active:
            # User is being reactivated - clear deactivation data
            instance.deactivation_reason = None
            instance.reactivation_instructions = None
            instance.deactivated_at = None
            instance.deactivated_by = None
        
        instance.is_active = is_active
        instance.save()
        instance.save()
        return instance

from dj_rest_auth.serializers import PasswordResetSerializer
from django.conf import settings

class CustomPasswordResetSerializer(PasswordResetSerializer):
    def save(self):
        request = self.context.get('request')
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        
        # Extract domain from FRONTEND_URL for domain_override if needed (stripping http/https)
        # But primarily we rely on 'frontend_url' context variable in the template.
        domain = frontend_url.replace('http://', '').replace('https://', '').split('/')[0]

        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL', None),
            'request': request,
            'domain_override': domain,
            'extra_email_context': {
                'domain': domain,
                'site_name': 'Royal Craft Jewelers',
                'frontend_url': frontend_url,
            },
            'email_template_name': 'registration/frontend_password_reset_email.html',
        }
        return self.reset_form.save(**opts)
