from django import forms
from cases.models import PatientCase
class PatientCaseForm(forms.ModelForm):
    class Meta:
        model = PatientCase
        fields = ['chief_complaint', 'symptoms', 'symptom_duration', 'medical_history', 'current_medications', 'allergies', 'previous_diseases', 'family_history', 'lifestyle_info', 'additional_info']
