from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User, PatientProfile, DoctorProfile, StaffProfile
from cases.models import PatientCase
from reports.models import TestRequest, MedicalReport
from ai_engine.models import AIAnalysis, DoctorDecision
from ai_engine.services.multimodal_service import MultimodalAnalysisService
from ai_engine.services.rag_service import RAGService
from ai_engine.services.llm_service import LLMService
import datetime


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def make_patient(username='testpatient', password='TestPass123!'):
    u = User.objects.create_user(username=username, password=password,
                                  role=User.ROLE_PATIENT, first_name='Test', last_name='Patient',
                                  email=f'{username}@test.com')
    PatientProfile.objects.create(user=u)
    return u

def make_doctor(username='testdoctor', password='TestPass123!'):
    u = User.objects.create_user(username=username, password=password,
                                  role=User.ROLE_DOCTOR, first_name='Test', last_name='Doctor',
                                  email=f'{username}@test.com')
    DoctorProfile.objects.create(user=u, specialization='General Medicine')
    return u

def make_staff(username='teststaff', password='TestPass123!'):
    u = User.objects.create_user(username=username, password=password,
                                  role=User.ROLE_STAFF, first_name='Test', last_name='Staff',
                                  email=f'{username}@test.com')
    StaffProfile.objects.create(user=u, department='Radiology')
    return u

def make_admin(username='testadmin', password='TestPass123!'):
    return User.objects.create_superuser(username=username, password=password,
                                          role=User.ROLE_ADMIN, email=f'{username}@test.com')

def make_case(patient, status=PatientCase.STATUS_SUBMITTED):
    return PatientCase.objects.create(
        patient=patient,
        chief_complaint='Test complaint',
        symptoms='Chest pain, fatigue',
        medical_history='Hypertension',
        status=status,
    )


# ─────────────────────────────────────────────
# Authentication Tests
# ─────────────────────────────────────────────

class AuthenticationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = make_patient()
        self.doctor = make_doctor()
        self.staff = make_staff()
        self.admin = make_admin()

    def test_login_page_loads(self):
        response = self.client.get(reverse('accounts:login'))
        self.assertEqual(response.status_code, 200)

    def test_register_page_loads(self):
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)

    def test_patient_login_redirects_to_patient_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testpatient', 'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('patients:dashboard'))

    def test_doctor_login_redirects_to_doctor_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testdoctor', 'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('doctors:dashboard'))

    def test_staff_login_redirects_to_staff_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'teststaff', 'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('staff:dashboard'))

    def test_admin_login_redirects_to_admin_dashboard(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testadmin', 'password': 'TestPass123!'
        })
        self.assertRedirects(response, reverse('administration:dashboard'))

    def test_invalid_login_shows_error(self):
        response = self.client.post(reverse('accounts:login'), {
            'username': 'testpatient', 'password': 'WrongPassword!'
        })
        self.assertEqual(response.status_code, 200)

    def test_logout_redirects_to_login(self):
        self.client.login(username='testpatient', password='TestPass123!')
        response = self.client.get(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))


# ─────────────────────────────────────────────
# Role-Based Access Control Tests
# ─────────────────────────────────────────────

class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = make_patient()
        self.doctor = make_doctor()
        self.staff = make_staff()
        self.admin = make_admin()

    def test_unauthenticated_redirected_from_patient_dashboard(self):
        response = self.client.get(reverse('patients:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_patient_cannot_access_doctor_dashboard(self):
        self.client.login(username='testpatient', password='TestPass123!')
        response = self.client.get(reverse('doctors:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_patient_cannot_access_staff_dashboard(self):
        self.client.login(username='testpatient', password='TestPass123!')
        response = self.client.get(reverse('staff:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_patient_cannot_access_admin_dashboard(self):
        self.client.login(username='testpatient', password='TestPass123!')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_doctor_cannot_access_patient_dashboard(self):
        self.client.login(username='testdoctor', password='TestPass123!')
        response = self.client.get(reverse('patients:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_doctor_cannot_access_admin_dashboard(self):
        self.client.login(username='testdoctor', password='TestPass123!')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_staff_cannot_access_admin_dashboard(self):
        self.client.login(username='teststaff', password='TestPass123!')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertNotEqual(response.status_code, 200)

    def test_patient_dashboard_accessible_to_patient(self):
        self.client.login(username='testpatient', password='TestPass123!')
        response = self.client.get(reverse('patients:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_doctor_dashboard_accessible_to_doctor(self):
        self.client.login(username='testdoctor', password='TestPass123!')
        response = self.client.get(reverse('doctors:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_staff_dashboard_accessible_to_staff(self):
        self.client.login(username='teststaff', password='TestPass123!')
        response = self.client.get(reverse('staff:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_dashboard_accessible_to_admin(self):
        self.client.login(username='testadmin', password='TestPass123!')
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# Patient Case Tests
# ─────────────────────────────────────────────

class PatientCaseTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = make_patient()
        self.patient2 = make_patient(username='testpatient2')
        self.client.login(username='testpatient', password='TestPass123!')

    def test_new_case_page_loads(self):
        response = self.client.get(reverse('patients:new_case'))
        self.assertEqual(response.status_code, 200)

    def test_patient_can_submit_case(self):
        response = self.client.post(reverse('patients:new_case'), {
            'chief_complaint': 'Chest pain',
            'symptoms': 'Severe chest pain and shortness of breath',
            'symptom_duration': '3 days',
            'medical_history': 'Hypertension',
            'current_medications': 'Amlodipine 5mg',
            'allergies': 'None',
            'previous_diseases': 'None',
            'family_history': 'Heart disease in father',
            'lifestyle_info': 'Non-smoker',
            'additional_info': '',
        })
        self.assertEqual(PatientCase.objects.filter(patient=self.patient).count(), 1)

    def test_patient_can_see_own_cases(self):
        case = make_case(self.patient)
        response = self.client.get(reverse('patients:my_cases'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Cases')
        # The case complaint should appear in the table
        self.assertContains(response, case.chief_complaint[:20])

    def test_patient_cannot_see_other_patients_case(self):
        other_case = make_case(self.patient2)
        response = self.client.get(
            reverse('patients:case_detail', kwargs={'case_id': other_case.case_id})
        )
        self.assertEqual(response.status_code, 404)

    def test_patient_can_see_own_case_detail(self):
        case = make_case(self.patient)
        response = self.client.get(
            reverse('patients:case_detail', kwargs={'case_id': case.case_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_case_created_with_submitted_status(self):
        case = make_case(self.patient)
        self.assertEqual(case.status, PatientCase.STATUS_SUBMITTED)


# ─────────────────────────────────────────────
# Doctor Workflow Tests
# ─────────────────────────────────────────────

class DoctorWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = make_patient()
        self.doctor = make_doctor()
        self.case = make_case(self.patient)
        self.client.login(username='testdoctor', password='TestPass123!')

    def test_doctor_can_list_cases(self):
        response = self.client.get(reverse('doctors:case_list'))
        self.assertEqual(response.status_code, 200)

    def test_doctor_can_view_case_detail(self):
        response = self.client.get(
            reverse('doctors:case_detail', kwargs={'case_id': self.case.case_id})
        )
        self.assertEqual(response.status_code, 200)

    def test_doctor_can_request_test(self):
        response = self.client.post(
            reverse('doctors:request_test', kwargs={'case_id': self.case.case_id}),
            {'test_type': 'BLOOD_TEST', 'instructions': 'Check CBC and lipid profile'}
        )
        self.assertEqual(TestRequest.objects.filter(case=self.case).count(), 1)
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, PatientCase.STATUS_TEST_REQUESTED)

    def test_doctor_can_verify_report(self):
        test_req = TestRequest.objects.create(
            case=self.case, doctor=self.doctor,
            test_type='BLOOD_TEST', status=TestRequest.STATUS_REPORT_UPLOADED
        )
        report = MedicalReport.objects.create(
            case=self.case, test_request=test_req, uploaded_by=self.doctor,
            report_type='BLOOD_REPORT', title='Blood Test',
            report_date=datetime.date.today(), status=MedicalReport.STATUS_UPLOADED
        )
        response = self.client.post(
            reverse('doctors:verify_report', kwargs={'report_id': report.id}),
            {'action': 'verify'}
        )
        report.refresh_from_db()
        self.assertEqual(report.status, MedicalReport.STATUS_VERIFIED)

    def test_doctor_can_run_ai_analysis(self):
        from unittest.mock import MagicMock, patch
        from django.test import override_settings

        # Build mock Gemini + ChromaDB so the AI pipeline completes without real API/data
        _CLINICAL_REPORT = (
            "1. PRIMARY PREDICTION\n   Test Condition (85%)\n"
            "2. CONFIDENCE INTERPRETATION\n   High.\n"
            "3. SUPPORTING FINDINGS\n   Fever.\n"
            "4. RELEVANT MEDICAL CONTEXT\n   Standard management.\n"
            "5. UNCERTAINTIES AND LIMITATIONS\n   Exam required.\n"
            "6. RECOMMENDED NEXT STEPS\n   Monitor.\n"
            "DISCLAIMER: This report is AI-generated decision support only."
        )

        # Gemini embed mock
        fake_embed_val = MagicMock()
        fake_embed_val.values = [0.01] * 768
        fake_embed_resp = MagicMock()
        fake_embed_resp.embeddings = [fake_embed_val]

        # Gemini generate mock
        fake_gen_resp = MagicMock()
        fake_gen_resp.text = _CLINICAL_REPORT

        mock_genai = MagicMock()
        mock_genai.models.embed_content.return_value = fake_embed_resp
        mock_genai.models.generate_content.return_value = fake_gen_resp

        # ChromaDB mock
        mock_coll = MagicMock()
        mock_coll.count.return_value = 3
        mock_coll.query.return_value = {
            "documents": [["Hypertension is a risk factor."]],
            "metadatas": [[{"topic": "Hypertension Management", "doc_id": "hypertension"}]],
            "distances": [[0.12]],
        }
        mock_chroma = MagicMock()
        mock_chroma.get_or_create_collection.return_value = mock_coll

        import ai_engine.services.rag_service as rs
        rs._rag_instance = None  # reset singleton

        with override_settings(GEMINI_API_KEY='fake-key-for-test', LLM_MODEL='gemini-2.5-flash'), \
             patch('chromadb.PersistentClient', return_value=mock_chroma), \
             patch('google.genai.Client', return_value=mock_genai):
            response = self.client.post(
                reverse('doctors:run_ai_analysis', kwargs={'case_id': self.case.case_id})
            )

        rs._rag_instance = None  # cleanup
        self.assertEqual(AIAnalysis.objects.filter(case=self.case).count(), 1)
        analysis = AIAnalysis.objects.get(case=self.case)
        self.assertEqual(analysis.status, AIAnalysis.STATUS_COMPLETED)
        self.assertNotEqual(analysis.prediction, '')

    def test_doctor_can_submit_final_decision(self):
        # Create an AI analysis first
        AIAnalysis.objects.create(
            case=self.case, initiated_by=self.doctor,
            prediction='Test Condition', confidence=0.85,
            status=AIAnalysis.STATUS_COMPLETED
        )
        response = self.client.post(
            reverse('doctors:submit_decision', kwargs={'case_id': self.case.case_id}),
            {
                'final_diagnosis': 'Hypertension Stage 2',
                'clinical_notes': 'Patient presents with elevated BP',
                'recommendation': 'Increase medication dosage',
                'treatment_advice': 'Amlodipine 10mg daily',
                'follow_up_instructions': 'Follow up in 4 weeks',
                'doctor_override': False,
                'override_reason': '',
            }
        )
        self.case.refresh_from_db()
        self.assertEqual(self.case.status, PatientCase.STATUS_COMPLETED)
        self.assertTrue(DoctorDecision.objects.filter(case=self.case).exists())


# ─────────────────────────────────────────────
# AI Service Tests
# ─────────────────────────────────────────────

class AIServiceTests(TestCase):

    _CLINICAL_REPORT = (
        "1. PRIMARY PREDICTION\n   Hypertensive Heart Disease\n"
        "2. CONFIDENCE INTERPRETATION\n   High confidence.\n"
        "3. SUPPORTING FINDINGS\n   Elevated BP, headache.\n"
        "4. RELEVANT MEDICAL CONTEXT\n   ACE inhibitors are first-line.\n"
        "5. UNCERTAINTIES AND LIMITATIONS\n   Exam required.\n"
        "6. RECOMMENDED NEXT STEPS\n   Confirm BP with serial measurements.\n"
        "DISCLAIMER: This report is AI-generated decision support only. "
        "The attending physician must make the final clinical assessment."
    )

    def setUp(self):
        from unittest.mock import MagicMock, patch
        self.patient = make_patient()
        self.case    = make_case(self.patient)

        # Build shared mock objects
        fake_embed_val = MagicMock()
        fake_embed_val.values = [0.01] * 768
        fake_embed_resp = MagicMock()
        fake_embed_resp.embeddings = [fake_embed_val]

        fake_gen_resp = MagicMock()
        fake_gen_resp.text = self._CLINICAL_REPORT

        self.mock_genai = MagicMock()
        self.mock_genai.models.embed_content.return_value  = fake_embed_resp
        self.mock_genai.models.generate_content.return_value = fake_gen_resp

        mock_coll = MagicMock()
        mock_coll.count.return_value = 3
        mock_coll.query.return_value = {
            "documents": [["Hypertension is a major risk factor.", "Diabetes info."]],
            "metadatas": [[
                {"topic": "Hypertension Management", "doc_id": "hypertension"},
                {"topic": "Diabetes",                "doc_id": "diabetes"},
            ]],
            "distances": [[0.10, 0.18]],
        }
        mock_coll.get.return_value = {"ids": []}
        self.mock_chroma = MagicMock()
        self.mock_chroma.get_or_create_collection.return_value = mock_coll

        # Reset RAG singleton before each test
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    def tearDown(self):
        import ai_engine.services.rag_service as rs
        rs._rag_instance = None

    def test_multimodal_service_returns_prediction(self):
        from unittest.mock import patch
        from django.test import override_settings
        with override_settings(GEMINI_API_KEY='fake-key', LLM_MODEL='gemini-2.5-flash'), \
             patch('chromadb.PersistentClient', return_value=self.mock_chroma), \
             patch('google.genai.Client', return_value=self.mock_genai):
            service = MultimodalAnalysisService()
            result  = service.analyze(self.case)
        self.assertIn('prediction', result)
        self.assertIn('confidence', result)
        self.assertIn('supporting_findings', result)
        self.assertIn('rag_context', result)
        self.assertIn('llm_explanation', result)
        self.assertNotEqual(result['prediction'], '')
        self.assertGreater(result['confidence'], 0)

    def test_rag_service_returns_context(self):
        from unittest.mock import patch
        from django.test import override_settings
        with override_settings(GEMINI_API_KEY='fake-key'), \
             patch('chromadb.PersistentClient', return_value=self.mock_chroma), \
             patch('google.genai.Client', return_value=self.mock_genai):
            rag     = RAGService()
            results = rag.retrieve('chest pain hypertension blood pressure', top_k=3)
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_llm_service_returns_explanation(self):
        from unittest.mock import patch
        from django.test import override_settings
        with override_settings(GEMINI_API_KEY='fake-key', LLM_MODEL='gemini-2.5-flash'), \
             patch('google.genai.Client', return_value=self.mock_genai):
            llm = LLMService()
            explanation = llm.generate_explanation({
                'symptoms':         'Chest pain and shortness of breath',
                'medical_history':  'Hypertension',
                'medications':      'None',
                'family_history':   'None',
                'prediction':       'Hypertensive Heart Disease',
                'confidence':       0.82,
                'rag_context':      ['Hypertension is a risk factor for heart disease'],
                'reports_summary':  'Normal CBC',
            })
        self.assertIsInstance(explanation, str)
        self.assertGreater(len(explanation), 50)

    def test_gemini_api_key_setting_exists(self):
        """GEMINI_API_KEY must be defined in settings (AI_MODE removed)."""
        from django.conf import settings
        # GEMINI_API_KEY exists in settings (may be empty placeholder in test env)
        self.assertTrue(hasattr(settings, 'GEMINI_API_KEY'))
        # AI_MODE is no longer used
        self.assertFalse(hasattr(settings, 'AI_MODE'))


# ─────────────────────────────────────────────
# Staff Workflow Tests
# ─────────────────────────────────────────────

class StaffWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.patient = make_patient()
        self.doctor = make_doctor()
        self.staff = make_staff()
        self.case = make_case(self.patient, status=PatientCase.STATUS_TEST_REQUESTED)
        self.test_req = TestRequest.objects.create(
            case=self.case, doctor=self.doctor,
            test_type='BLOOD_TEST', status=TestRequest.STATUS_PENDING
        )
        self.client.login(username='teststaff', password='TestPass123!')

    def test_staff_can_see_test_requests(self):
        response = self.client.get(reverse('staff:test_requests'))
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_test_request_detail(self):
        response = self.client.get(
            reverse('staff:test_request_detail', kwargs={'request_id': self.test_req.id})
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_can_view_my_reports(self):
        response = self.client.get(reverse('staff:my_reports'))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# Admin Tests
# ─────────────────────────────────────────────

class AdminWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = make_admin()
        self.client.login(username='testadmin', password='TestPass123!')

    def test_admin_can_access_dashboard(self):
        response = self.client.get(reverse('administration:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_list_users(self):
        response = self.client.get(reverse('administration:user_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_dataset_list(self):
        response = self.client.get(reverse('administration:dataset_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_ai_model_list(self):
        response = self.client.get(reverse('administration:ai_model_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_audit_logs(self):
        response = self.client.get(reverse('administration:audit_log_list'))
        self.assertEqual(response.status_code, 200)

    def test_admin_can_access_all_cases(self):
        response = self.client.get(reverse('administration:case_list'))
        self.assertEqual(response.status_code, 200)


# ─────────────────────────────────────────────
# Model Tests
# ─────────────────────────────────────────────

class ModelTests(TestCase):
    def test_user_role_properties(self):
        p = make_patient(username='p1')
        d = make_doctor(username='d1')
        s = make_staff(username='s1')
        a = make_admin(username='a1')
        self.assertTrue(p.is_patient)
        self.assertFalse(p.is_doctor)
        self.assertTrue(d.is_doctor)
        self.assertTrue(s.is_staff_member)
        self.assertTrue(a.is_administrator)

    def test_case_status_lifecycle(self):
        patient = make_patient(username='lifecyclepatient')
        case = make_case(patient)
        self.assertEqual(case.status, PatientCase.STATUS_SUBMITTED)
        case.status = PatientCase.STATUS_UNDER_REVIEW
        case.save()
        case.refresh_from_db()
        self.assertEqual(case.status, PatientCase.STATUS_UNDER_REVIEW)

    def test_case_uuid_is_unique(self):
        patient = make_patient(username='uuidpatient')
        case1 = make_case(patient)
        case2 = make_case(patient)
        self.assertNotEqual(case1.case_id, case2.case_id)

    def test_patient_can_only_see_own_cases(self):
        p1 = make_patient(username='own1')
        p2 = make_patient(username='own2')
        make_case(p1)
        make_case(p2)
        p1_cases = PatientCase.objects.filter(patient=p1)
        self.assertEqual(p1_cases.count(), 1)
        self.assertFalse(p1_cases.filter(patient=p2).exists())
