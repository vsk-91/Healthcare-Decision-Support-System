from django.core.management.base import BaseCommand
from accounts.models import User, DoctorProfile, StaffProfile, PatientProfile
from cases.models import PatientCase
from reports.models import TestRequest, MedicalReport
from ai_engine.models import AIModel, AIAnalysis, DoctorDecision
from datasets.models import Dataset
from audit.models import AuditLog

class Command(BaseCommand):
    help = 'Seeds demo data for Healthcare DSS'

    def handle(self, *args, **options):
        # Admin
        admin, _ = User.objects.get_or_create(username='admin', defaults={
            'role': User.ROLE_ADMIN, 'is_superuser': True, 'is_staff': True
        })
        admin.set_password('Admin@1234')
        admin.save()

        # Doctor
        doc, _ = User.objects.get_or_create(username='doctor1', defaults={
            'role': User.ROLE_DOCTOR, 'first_name': 'James', 'last_name': 'Wilson'
        })
        doc.set_password('Doctor@1234')
        doc.save()
        DoctorProfile.objects.get_or_create(user=doc, defaults={'specialization': 'Internal Medicine', 'license_number': 'MED-2024-001'})

        # Staff
        staff, _ = User.objects.get_or_create(username='staff1', defaults={
            'role': User.ROLE_STAFF, 'first_name': 'Sarah', 'last_name': 'Johnson'
        })
        staff.set_password('Staff@1234')
        staff.save()
        StaffProfile.objects.get_or_create(user=staff, defaults={'department': 'Radiology', 'employee_id': 'EMP-001'})

        # Patient 1 (Completed Case)
        p1, _ = User.objects.get_or_create(username='patient1', defaults={
            'role': User.ROLE_PATIENT, 'first_name': 'John', 'last_name': 'Smith'
        })
        p1.set_password('Patient@1234')
        p1.save()
        PatientProfile.objects.get_or_create(user=p1, defaults={'blood_group': 'O+'})

        case1, _ = PatientCase.objects.get_or_create(patient=p1, defaults={
            'status': PatientCase.STATUS_COMPLETED,
            'symptoms': 'Persistent chest pain, shortness of breath, fatigue for 2 weeks',
            'assigned_doctor': doc
        })
        
        tr1, _ = TestRequest.objects.get_or_create(case=case1, doctor=doc, test_type='BLOOD_TEST', defaults={'status': TestRequest.STATUS_VERIFIED})
        tr2, _ = TestRequest.objects.get_or_create(case=case1, doctor=doc, test_type='XRAY', defaults={'status': TestRequest.STATUS_VERIFIED})
        
        MedicalReport.objects.get_or_create(case=case1, test_request=tr1, uploaded_by=staff, defaults={
            'report_type': 'BLOOD_REPORT', 'title': 'Blood Work', 'report_date': '2024-01-01', 'status': MedicalReport.STATUS_VERIFIED, 'verified_by': doc
        })
        MedicalReport.objects.get_or_create(case=case1, test_request=tr2, uploaded_by=staff, defaults={
            'report_type': 'XRAY', 'title': 'Chest X-Ray', 'report_date': '2024-01-01', 'status': MedicalReport.STATUS_VERIFIED, 'verified_by': doc
        })

        ai1, _ = AIAnalysis.objects.get_or_create(case=case1, defaults={
            'status': AIAnalysis.STATUS_COMPLETED,
            'prediction': 'Hypertensive Heart Disease',
            'confidence': 0.82
        })
        
        DoctorDecision.objects.get_or_create(case=case1, doctor=doc, defaults={
            'ai_analysis': ai1,
            'final_diagnosis': 'Hypertensive Heart Disease - Stage 2',
            'recommendation': 'Continue antihypertensive therapy. Increase Amlodipine to 10mg daily.'
        })

        # Patient 2 (Pending AI Analysis)
        p2, _ = User.objects.get_or_create(username='patient2', defaults={
            'role': User.ROLE_PATIENT, 'first_name': 'Emily', 'last_name': 'Davis'
        })
        p2.set_password('Patient@1234')
        p2.save()
        PatientProfile.objects.get_or_create(user=p2)

        case2, _ = PatientCase.objects.get_or_create(patient=p2, defaults={
            'status': PatientCase.STATUS_REPORT_VERIFIED,
            'symptoms': 'High fever (39.5°C), productive cough, chest tightness for 5 days',
            'assigned_doctor': doc
        })

        # Dataset & AI Model
        Dataset.objects.get_or_create(name='Demo Healthcare Dataset v1.0', defaults={'status': Dataset.STATUS_ACTIVE})
        AIModel.objects.get_or_create(name='Healthcare DL Classifier', defaults={'version': '1.0', 'model_type': 'MULTIMODAL', 'status': AIModel.STATUS_ACTIVE, 'accuracy': 0.85})

        AuditLog.objects.create(user=admin, action='SYSTEM', description='Demo data seeded')

        self.stdout.write(self.style.SUCCESS('Successfully seeded demo data'))
