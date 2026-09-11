from django import forms
from reports.models import MedicalReport
class MedicalReportUploadForm(forms.ModelForm):
    class Meta:
        model = MedicalReport
        fields = ['report_type', 'title', 'description', 'file', 'report_date']
