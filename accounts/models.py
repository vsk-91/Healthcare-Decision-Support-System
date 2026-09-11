from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_PATIENT = 'PATIENT'
    ROLE_DOCTOR = 'DOCTOR'
    ROLE_STAFF = 'STAFF'
    ROLE_ADMIN = 'ADMIN'
    
    ROLE_CHOICES = [
        (ROLE_PATIENT, 'Patient'),
        (ROLE_DOCTOR, 'Doctor'),
        (ROLE_STAFF, 'Staff'),
        (ROLE_ADMIN, 'Administrator'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_PATIENT)
    phone = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M','Male'),('F','Female'),('O','Other')], blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    @property
    def is_patient(self): return self.role == self.ROLE_PATIENT
    @property
    def is_doctor(self): return self.role == self.ROLE_DOCTOR
    @property
    def is_staff_member(self): return self.role == self.ROLE_STAFF
    @property
    def is_administrator(self): return self.role == self.ROLE_ADMIN
    
    def get_full_name_or_username(self):
        return self.get_full_name() or self.username

class PatientProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='patient_profile')
    emergency_contact = models.CharField(max_length=100, blank=True)
    emergency_phone = models.CharField(max_length=20, blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    insurance_number = models.CharField(max_length=50, blank=True)
    
    def __str__(self): return f"Patient: {self.user.get_full_name_or_username()}"

class DoctorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100, blank=True)
    license_number = models.CharField(max_length=50, blank=True)
    department = models.CharField(max_length=100, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    
    def __str__(self): return f"Dr. {self.user.get_full_name_or_username()}"

class StaffProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    department = models.CharField(max_length=100, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    
    def __str__(self): return f"Staff: {self.user.get_full_name_or_username()}"
