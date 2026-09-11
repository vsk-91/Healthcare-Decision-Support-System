from django.db import models
from accounts.models import User


class Dataset(models.Model):
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_INACTIVE = 'INACTIVE'
    STATUS_PROCESSING = 'PROCESSING'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_INACTIVE, 'Inactive'),
        (STATUS_PROCESSING, 'Processing'),
    ]
    DATASET_TYPES = [
        ('TABULAR', 'Tabular'),
        ('IMAGE', 'Image'),
        ('TEXT', 'Text'),
        ('MULTIMODAL', 'Multimodal'),
    ]

    name = models.CharField(max_length=200)
    version = models.CharField(max_length=50, default='1.0')
    description = models.TextField(blank=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default=STATUS_INACTIVE)
    dataset_type = models.CharField(max_length=20, choices=DATASET_TYPES, blank=True)
    file = models.FileField(upload_to='datasets/', blank=True, null=True)
    record_count = models.PositiveIntegerField(null=True, blank=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} v{self.version}"
