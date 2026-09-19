import os
import django

# Replace 'healthcare_dss.settings' with your actual Django settings path if different
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_dss.settings')
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
            "is_staff": True,
            "is_superuser": True,
            "is_active": True,
        }
    )

    if created:
        user.set_password(password)
        user.save()
        print("Superuser created successfully.")

    # Clean up patient profile if automatically created by signals
    PatientProfile.objects.filter(user=user).delete()

    # Link to staff profile for admin access
    StaffProfile.objects.get_or_create(user=user)
    print("Staff profile assigned successfully.")

if __name__ == "__main__":
    make_admin()