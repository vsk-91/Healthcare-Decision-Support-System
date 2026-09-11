from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from cases.models import PatientCase
from .forms import PatientCaseForm
from accounts.decorators import patient_required

@patient_required
def dashboard(request):
    from reports.models import TestRequest
    cases = PatientCase.objects.filter(patient=request.user)
    active_cases = cases.exclude(status=PatientCase.STATUS_COMPLETED).count()
    completed_cases = cases.filter(status=PatientCase.STATUS_COMPLETED).count()
    pending_tests = TestRequest.objects.filter(case__patient=request.user, status=TestRequest.STATUS_PENDING).count()
    context = {
        'total_cases': cases.count(),
        'active_cases': active_cases,
        'completed_cases': completed_cases,
        'pending_tests': pending_tests,
        'recent_cases': cases[:5],
    }
    return render(request, 'patient/dashboard.html', context)


@patient_required
def new_case(request):
    if request.method == 'POST':
        form = PatientCaseForm(request.POST)
        if form.is_valid():
            case = form.save(commit=False)
            case.patient = request.user
            case.save()
            return redirect('patients:my_cases')
    else:
        form = PatientCaseForm()
    return render(request, 'patient/new_case.html', {'form': form})

@patient_required
def my_cases(request):
    cases = PatientCase.objects.filter(patient=request.user)
    return render(request, 'patient/my_cases.html', {'cases': cases})

@patient_required
def case_detail(request, case_id):
    case = get_object_or_404(PatientCase, case_id=case_id, patient=request.user)
    return render(request, 'patient/case_detail.html', {'case': case})

@patient_required
def results(request):
    cases = PatientCase.objects.filter(patient=request.user, status=PatientCase.STATUS_COMPLETED)
    return render(request, 'patient/results.html', {'cases': cases})
