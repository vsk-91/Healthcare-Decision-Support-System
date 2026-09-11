from django import forms
from reports.models import TestRequest, MedicalReport
from ai_engine.models import DoctorDecision

class TestRequestForm(forms.ModelForm):
    class Meta:
        model = TestRequest
        fields = ['test_type', 'instructions', 'notes']

class DoctorDecisionForm(forms.ModelForm):
    class Meta:
        model = DoctorDecision
        fields = ['final_diagnosis', 'clinical_notes', 'recommendation', 'treatment_advice', 'follow_up_instructions', 'doctor_override', 'override_reason']
