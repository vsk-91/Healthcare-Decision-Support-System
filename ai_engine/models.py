from django.db import models
from accounts.models import User
from cases.models import PatientCase


class AIModel(models.Model):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_TRAINING = 'TRAINING'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_TRAINING, 'Training'),
        (STATUS_FAILED, 'Failed'),
    ]
    MODEL_TYPES = [
        ('CLASSIFICATION', 'Classification'),
        ('DETECTION', 'Detection'),
        ('SEGMENTATION', 'Segmentation'),
        ('MULTIMODAL', 'Multimodal'),
        ('NLP', 'NLP'),
    ]

    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    description = models.TextField(blank=True)
    model_file = models.FileField(upload_to='ai_models/', blank=True, null=True)
    accuracy = models.FloatField(null=True, blank=True)
    precision = models.FloatField(null=True, blank=True)
    recall = models.FloatField(null=True, blank=True)
    f1_score = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_INACTIVE)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    trained_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} v{self.version}"


class AIAnalysis(models.Model):
    STATUS_PENDING = 'PENDING'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    case = models.ForeignKey(PatientCase, on_delete=models.CASCADE, related_name='ai_analyses')
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, blank=True)
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prediction = models.CharField(max_length=200, blank=True)
    confidence = models.FloatField(null=True, blank=True)
    supporting_findings = models.TextField(blank=True)
    rag_context = models.TextField(blank=True)
    llm_explanation = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analysis for {self.case} — {self.prediction}"


class DoctorDecision(models.Model):
    case = models.OneToOneField(PatientCase, on_delete=models.CASCADE, related_name='doctor_decision')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='decisions')
    ai_analysis = models.ForeignKey(AIAnalysis, on_delete=models.SET_NULL, null=True, blank=True)
    final_diagnosis = models.TextField()
    clinical_notes = models.TextField(blank=True)
    recommendation = models.TextField()
    treatment_advice = models.TextField(blank=True)
    follow_up_instructions = models.TextField(blank=True)
    doctor_override = models.BooleanField(default=False)
    override_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Decision for {self.case} by {self.doctor}"
