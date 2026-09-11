from django.db import models
from accounts.models import User
from cases.models import PatientCase

class TestRequest(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_ASSIGNED = 'ASSIGNED'
    STATUS_IN_PROGRESS = 'IN_PROGRESS'
    STATUS_REPORT_UPLOADED = 'REPORT_UPLOADED'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_REJECTED = 'REJECTED'
    STATUS_COMPLETED = 'COMPLETED'
    
    STATUS_CHOICES = [(STATUS_PENDING, 'Pending'), (STATUS_ASSIGNED, 'Assigned'), (STATUS_IN_PROGRESS, 'In Progress'), (STATUS_REPORT_UPLOADED, 'Report Uploaded'), (STATUS_VERIFIED, 'Verified'), (STATUS_REJECTED, 'Rejected'), (STATUS_COMPLETED, 'Completed')]
    TEST_TYPES = [('BLOOD_TEST', 'Blood Test'), ('XRAY', 'X-Ray'), ('MRI', 'MRI Scan'), ('CT_SCAN', 'CT Scan'), ('ULTRASOUND', 'Ultrasound'), ('ECG', 'ECG'), ('URINE_TEST', 'Urine Test'), ('BIOPSY', 'Biopsy'), ('OTHER', 'Other')]
    
    case = models.ForeignKey(PatientCase, on_delete=models.CASCADE, related_name='test_requests')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_requests_made')
    assigned_staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='test_requests_assigned')
    test_type = models.CharField(max_length=20, choices=TEST_TYPES)
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    requested_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

class MedicalReport(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_UPLOADED = 'UPLOADED'
    STATUS_VERIFIED = 'VERIFIED'
    STATUS_REJECTED = 'REJECTED'
    
    STATUS_CHOICES = [(STATUS_PENDING, 'Pending'), (STATUS_UPLOADED, 'Uploaded'), (STATUS_VERIFIED, 'Verified'), (STATUS_REJECTED, 'Rejected')]
    REPORT_TYPES = [('XRAY', 'X-Ray'), ('MRI', 'MRI Scan'), ('CT_SCAN', 'CT Scan'), ('ULTRASOUND', 'Ultrasound'), ('BLOOD_REPORT', 'Blood Report'), ('LAB_REPORT', 'Laboratory Report'), ('ECG', 'ECG Report'), ('PATHOLOGY', 'Pathology Report'), ('OTHER', 'Other')]
    
    case = models.ForeignKey(PatientCase, on_delete=models.CASCADE, related_name='medical_reports')
    test_request = models.ForeignKey(TestRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_reports')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='reports/%Y/%m/%d/', blank=True)
    report_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_UPLOADED)
    verification_notes = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    def is_image(self): return self.report_type in ['XRAY', 'MRI', 'CT_SCAN', 'ULTRASOUND']
