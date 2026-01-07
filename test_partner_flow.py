"""
Test script to verify partner registration and login flow
Run this with: python manage.py shell < test_partner_flow.py
Or: python manage.py shell
Then copy-paste the code below
"""

from django.contrib.auth.models import User
from frontend.models import UserProfile

# Test 1: Check if a user exists and their partner status
print("=" * 50)
print("TESTING PARTNER REGISTRATION AND LOGIN FLOW")
print("=" * 50)

# Get all users
users = User.objects.all()
print(f"\nTotal users in database: {users.count()}")

for user in users:
    try:
        profile = UserProfile.objects.get(user=user)
        print(f"\nUser: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  Is Partner: {profile.is_partner}")
        print(f"  Phone: {profile.phone}")
    except UserProfile.DoesNotExist:
        print(f"\nUser: {user.username} - NO PROFILE FOUND!")

print("\n" + "=" * 50)
print("To test registration:")
print("1. Go to /register/")
print("2. Fill in the form")
print("3. Check 'Register as Partner' checkbox")
print("4. Submit")
print("5. Run this script again to verify is_partner=True")
print("=" * 50)

