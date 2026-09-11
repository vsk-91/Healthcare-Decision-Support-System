from django.shortcuts import render, redirect, get_object_or_404
from cases.models import PatientCase
from reports.models import TestRequest, MedicalReport
from ai_engine.models import AIAnalysis, DoctorDecision
from ai_engine.services.multimodal_service import MultimodalAnalysisService
from .forms import TestRequestForm, DoctorDecisionForm
from accounts.decorators import doctor_required
from audit.utils import log_action

STATUS_STEPS = [
    ('SUBMITTED', 'Submitted'),
    ('UNDER_REVIEW', 'Under Review'),
    ('TEST_REQUESTED', 'Test Requested'),
    ('AWAITING_REPORT', 'Awaiting Report'),
    ('REPORT_UPLOADED', 'Report Uploaded'),
    ('REPORT_VERIFIED', 'Report Verified'),
    ('AI_ANALYSIS', 'AI Analysis'),
    ('DOCTOR_REVIEW', 'Doctor Review'),
    ('FINAL_DECISION', 'Final Decision'),
    ('COMPLETED', 'Completed'),
]

def get_completed_steps(current_status):
    steps = [s[0] for s in STATUS_STEPS]
    try:
        idx = steps.index(current_status)
        return steps[:idx]
    except ValueError:
        return []


@doctor_required
def dashboard(request):
    cases = PatientCase.objects.all()
    context = {
        'total_cases': cases.count(),
        'new_cases': cases.filter(status=PatientCase.STATUS_SUBMITTED).count(),
        'test_requested': cases.filter(status=PatientCase.STATUS_TEST_REQUESTED).count(),
        'awaiting_verification': cases.filter(status=PatientCase.STATUS_REPORT_UPLOADED).count(),
        'ready_for_ai': cases.filter(status=PatientCase.STATUS_REPORT_VERIFIED).count(),
        'awaiting_decision': cases.filter(status=PatientCase.STATUS_AI_ANALYSIS).count(),
        'completed': cases.filter(status=PatientCase.STATUS_COMPLETED).count(),
        'recent_cases': cases[:8],
    }
    return render(request, 'doctor/dashboard.html', context)


@doctor_required
def case_list(request):
    status_filter = request.GET.get('status', '')
    cases = PatientCase.objects.all()
    if status_filter:
        cases = cases.filter(status=status_filter)
    status_choices = PatientCase.STATUS_CHOICES
    return render(request, 'doctor/case_list.html', {
        'cases': cases,
        'status_filter': status_filter,
        'status_choices': status_choices,
    })


@doctor_required
def case_detail(request, case_id):
    case = get_object_or_404(PatientCase, case_id=case_id)
    # Update status to UNDER_REVIEW when doctor opens case
    if case.status == PatientCase.STATUS_SUBMITTED:
        case.status = PatientCase.STATUS_UNDER_REVIEW
        case.assigned_doctor = request.user
        case.save()
    test_form = TestRequestForm()
    decision_form = DoctorDecisionForm()
    completed_steps = get_completed_steps(case.status)
    return render(request, 'doctor/case_detail.html', {
        'case': case,
        'test_form': test_form,
        'decision_form': decision_form,
        'status_steps': STATUS_STEPS,
        'completed_steps': completed_steps,
    })


@doctor_required
def request_test(request, case_id):
    case = get_object_or_404(PatientCase, case_id=case_id)
    if request.method == 'POST':
        form = TestRequestForm(request.POST)
        if form.is_valid():
            test_req = form.save(commit=False)
            test_req.case = case
            test_req.doctor = request.user
            test_req.save()
            case.status = PatientCase.STATUS_TEST_REQUESTED
            case.save()
            log_action(request.user, 'TEST_REQUEST',
                       f'Requested {test_req.get_test_type_display()} for case {case.case_id}', request)
    return redirect('doctors:case_detail', case_id=case.case_id)


@doctor_required
def verify_report(request, report_id):
    report = get_object_or_404(MedicalReport, id=report_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            report.status = MedicalReport.STATUS_VERIFIED
            report.verified_by = request.user
            from django.utils import timezone
            report.verified_at = timezone.now()
            report.save()
            # Update case status to REPORT_VERIFIED if any report is now verified
            report.case.status = PatientCase.STATUS_REPORT_VERIFIED
            report.case.save()
            if report.test_request:
                report.test_request.status = TestRequest.STATUS_VERIFIED
                report.test_request.save()
            log_action(request.user, 'REPORT_VERIFY',
                       f'Verified report "{report.title}" for case {report.case.case_id}', request)
        elif action == 'reject':
            reason = request.POST.get('rejection_reason', '')
            report.status = MedicalReport.STATUS_REJECTED
            report.verification_notes = reason
            report.save()
            if report.test_request:
                report.test_request.status = TestRequest.STATUS_REJECTED
                report.test_request.save()
            log_action(request.user, 'REPORT_REJECT',
                       f'Rejected report "{report.title}" for case {report.case.case_id}', request)
    return redirect('doctors:case_detail', case_id=report.case.case_id)


@doctor_required
def run_ai_analysis(request, case_id):
    case = get_object_or_404(PatientCase, case_id=case_id)
    if request.method == 'POST':
        case.status = PatientCase.STATUS_AI_ANALYSIS
        case.save()
        service = MultimodalAnalysisService()
        result = service.analyze(case)
        AIAnalysis.objects.create(
            case=case,
            initiated_by=request.user,
            prediction=result['prediction'],
            confidence=result['confidence'],
            supporting_findings='\n'.join(result['supporting_findings']),
            rag_context='\n'.join(result['rag_context']),
            llm_explanation=result['llm_explanation'],
            status=AIAnalysis.STATUS_COMPLETED,
        )
        case.status = PatientCase.STATUS_DOCTOR_REVIEW
        case.save()
        log_action(request.user, 'AI_ANALYSIS',
                   f'Ran AI analysis on case {case.case_id} (mode: {result.get("mode","mock")})', request)
    return redirect('doctors:case_detail', case_id=case.case_id)


@doctor_required
def submit_decision(request, case_id):
    case = get_object_or_404(PatientCase, case_id=case_id)
    if request.method == 'POST':
        form = DoctorDecisionForm(request.POST)
        if form.is_valid():
            decision = form.save(commit=False)
            decision.case = case
            decision.doctor = request.user
            decision.ai_analysis = case.ai_analyses.last()
            decision.save()
            case.status = PatientCase.STATUS_COMPLETED
            case.save()
            log_action(request.user, 'FINAL_DECISION',
                       f'Submitted final decision for case {case.case_id}: {decision.final_diagnosis[:50]}', request)
    return redirect('doctors:case_detail', case_id=case.case_id)
