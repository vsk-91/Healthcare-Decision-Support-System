from django.contrib import admin
from .models import User, PatientProfile, DoctorProfile, StaffProfile

admin.site.register(User)
admin.site.register(PatientProfile)
admin.site.register(DoctorProfile)
admin.site.register(StaffProfile)
