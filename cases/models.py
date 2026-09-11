import uuid
from django.db import models
from accounts.models import User

class PatientCase(models.Model):
    STATUS_SUBMITTED = 'SUBMITTED'
    STATUS_UNDER_REVIEW = 'UNDER_REVIEW'
    STATUS_TEST_REQUESTED = 'TEST_REQUESTED'
    STATUS_AWAITING_REPORT = 'AWAITING_REPORT'
    STATUS_REPORT_UPLOADED = 'REPORT_UPLOADED'
    STATUS_REPORT_VERIFIED = 'REPORT_VERIFIED'
    STATUS_AI_ANALYSIS = 'AI_ANALYSIS'
    STATUS_DOCTOR_REVIEW = 'DOCTOR_REVIEW'
    STATUS_FINAL_DECISION = 'FINAL_DECISION'
    STATUS_COMPLETED = 'COMPLETED'
    
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_UNDER_REVIEW, 'Under Review'),
        (STATUS_TEST_REQUESTED, 'Test Requested'),
        (STATUS_AWAITING_REPORT, 'Awaiting Report'),
        (STATUS_REPORT_UPLOADED, 'Report Uploaded'),
        (STATUS_REPORT_VERIFIED, 'Report Verified'),
        (STATUS_AI_ANALYSIS, 'AI Analysis'),
        (STATUS_DOCTOR_REVIEW, 'Doctor Review'),
        (STATUS_FINAL_DECISION, 'Final Decision'),
        (STATUS_COMPLETED, 'Completed'),
    ]
    
    case_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cases')
    assigned_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_cases')
    
    # Symptoms & History
    chief_complaint = models.TextField()
    symptoms = models.TextField()
    symptom_duration = models.CharField(max_length=100, blank=True)
    medical_history = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    previous_diseases = models.TextField(blank=True)
    family_history = models.TextField(blank=True)
    lifestyle_info = models.TextField(blank=True)
    additional_info = models.TextField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self): return f"Case {str(self.case_id)[:8]} - {self.patient.get_full_name_or_username()}"
    
    def get_status_color(self):
        colors = {
            'SUBMITTED': 'info',
            'UNDER_REVIEW': 'primary',
            'TEST_REQUESTED': 'warning',
            'AWAITING_REPORT': 'warning',
            'REPORT_UPLOADED': 'secondary',
            'REPORT_VERIFIED': 'success',
            'AI_ANALYSIS': 'primary',
            'DOCTOR_REVIEW': 'primary',
            'FINAL_DECISION': 'success',
            'COMPLETED': 'success',
        }
        return colors.get(self.status, 'secondary')
