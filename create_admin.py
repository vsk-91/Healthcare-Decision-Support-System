import os
import sys
import django

# Look for settings.py automatically in the project directory
possible_settings = []
for root, dirs, files in os.walk('.'):
    if 'settings.py' in files:
        # Convert path like ./myproject/settings.py to myproject.settings
        rel_path = os.relpath(os.path.join(root, 'settings'), '.')
        module_path = rel_path.replace(os.sep, '.').strip('.')
        possible_settings.append(module_path)

if possible_settings:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', possible_settings[0])
    print(f"Using settings module: {possible_settings[0]}")
else:
    raise RuntimeError("Could not automatically locate settings.py in your project.")

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
    else:
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