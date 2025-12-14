import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'jewelry_orders.settings')
django.setup()

from users.serializers import UserRegistrationSerializer
from users.models import CustomUser

print("--- Testing Phone Constraints ---")

# 1. Test Valid Phone
print("\nTest 1: Valid Phone (1234567890)")
data1 = {
    'username': 'testuser_valid',
    'email': 'valid@example.com',
    'password': 'password123',
    'password_confirm': 'password123',
    'phone': '1234567890'
}
ser1 = UserRegistrationSerializer(data=data1)
if ser1.is_valid():
    try:
        ser1.save()
        print("Success: User created with valid phone.")
    except Exception as e:
        print(f"Error saving valid user: {e}")
else:
    print(f"Failed: {ser1.errors}")

# 2. Test Invalid Phone (Short)
print("\nTest 2: Invalid Phone (123)")
data2 = {
    'username': 'testuser_invalid1',
    'email': 'invalid1@example.com',
    'password': 'password123',
    'password_confirm': 'password123',
    'phone': '123'
}
ser2 = UserRegistrationSerializer(data=data2)
if not ser2.is_valid():
    print(f"Success: Caught invalid phone: {ser2.errors.get('phone')}")
else:
    print("Failed: Invalid phone was accepted!")

# 3. Test Invalid Phone (Non-numeric)
print("\nTest 3: Invalid Phone (abcdefghij)")
data3 = {
    'username': 'testuser_invalid2',
    'email': 'invalid2@example.com',
    'password': 'password123',
    'password_confirm': 'password123',
    'phone': 'abcdefghij'
}
ser3 = UserRegistrationSerializer(data=data3)
if not ser3.is_valid():
    print(f"Success: Caught non-numeric phone: {ser3.errors.get('phone')}")
else:
    print("Failed: Non-numeric phone was accepted!")

# 4. Test Duplicate Phone
print("\nTest 4: Duplicate Phone (1234567890)")
data4 = {
    'username': 'testuser_duplicate',
    'email': 'duplicate@example.com',
    'password': 'password123',
    'password_confirm': 'password123',
    'phone': '1234567890' # Same as Test 1
}
ser4 = UserRegistrationSerializer(data=data4)
# Serializer might pass is_valid() if it doesn't check DB uniqueness explicitly in validate()
# but save() should fail or UniqueValidator should catch it. 
# DRF ModelSerializer default UniqueValidator usually runs during is_valid().
if not ser4.is_valid():
    print(f"Success: Caught duplicate phone: {ser4.errors.get('phone')}")
else:
    # If is_valid passes, try save
    try:
        ser4.save()
        print("Failed: Duplicate phone was saved!")
    except Exception as e:
        print(f"Success: DB constraint caught duplicate: {e}")

# Cleanup
print("\nCleaning up test users...")
CustomUser.objects.filter(username__in=['testuser_valid']).delete()
print("Cleanup done.")
