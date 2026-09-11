from django import forms
from .models import Dataset


class DatasetUploadForm(forms.ModelForm):
    class Meta:
        model = Dataset
        fields = ['name', 'version', 'description', 'dataset_type', 'file', 'record_count', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
