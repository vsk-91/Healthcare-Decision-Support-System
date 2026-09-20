import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import StaffProfile, PatientProfile

User = get_user_model()

def make_admin():
    email = "admin@example.com"
    username = "admin"
    password = "AdminSecurePassword123!"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "role": User.ROLE_ADMIN,
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
    )

    if created:
        user.set_password(password)
        user.save()
        print("Superuser created successfully.")
    else:
        user.role = User.ROLE_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        print("Updated existing user to Superuser.")

    # Remove PatientProfile if created automatically by signals
    PatientProfile.objects.filter(user=user).delete()

    # Link to StaffProfile
    StaffProfile.objects.get_or_create(user=user)
    print("Staff profile assigned successfully.")

if __name__ == "__main__":
    make_admin()