from django.shortcuts import render, redirect, get_object_or_404
from reports.models import TestRequest, MedicalReport
from cases.models import PatientCase
from .forms import MedicalReportUploadForm
from accounts.decorators import staff_required
from audit.utils import log_action
import datetime


@staff_required
def dashboard(request):
    pending = TestRequest.objects.filter(status=TestRequest.STATUS_PENDING)
    in_progress = TestRequest.objects.filter(status=TestRequest.STATUS_IN_PROGRESS).count()
    my_reports = MedicalReport.objects.filter(uploaded_by=request.user).count()
    return render(request, 'staff/dashboard.html', {
        'pending_requests': pending.count(),
        'in_progress': in_progress,
        'my_reports_count': my_reports,
        'pending_list': pending[:10],
    })


@staff_required
def test_requests(request):
    status_filter = request.GET.get('status', TestRequest.STATUS_PENDING)
    requests = TestRequest.objects.filter(status=status_filter)
    return render(request, 'staff/test_requests.html', {
        'requests': requests,
        'status_filter': status_filter,
        'status_choices': TestRequest.STATUS_CHOICES,
    })


@staff_required
def test_request_detail(request, request_id):
    req = get_object_or_404(TestRequest, id=request_id)
    # Mark as in-progress when opened
    if req.status == TestRequest.STATUS_PENDING:
        req.status = TestRequest.STATUS_IN_PROGRESS
        req.assigned_staff = request.user
        req.save()
    form = MedicalReportUploadForm(initial={'report_date': datetime.date.today()})
    return render(request, 'staff/test_request_detail.html', {
        'req': req,
        'form': form,
        'today': datetime.date.today().isoformat(),
    })


@staff_required
def upload_report(request, request_id):
    req = get_object_or_404(TestRequest, id=request_id)
    if request.method == 'POST':
        form = MedicalReportUploadForm(request.POST, request.FILES)
        if form.is_valid():
            report = form.save(commit=False)
            report.test_request = req
            report.case = req.case
            report.uploaded_by = request.user
            report.status = MedicalReport.STATUS_UPLOADED
            report.save()
            req.status = TestRequest.STATUS_REPORT_UPLOADED
            req.save()
            req.case.status = PatientCase.STATUS_REPORT_UPLOADED
            req.case.save()
            log_action(request.user, 'REPORT_UPLOAD',
                       f'Uploaded report "{report.title}" for test request {req.id}', request)
            return redirect('staff:test_requests')
        else:
            return render(request, 'staff/test_request_detail.html', {
                'req': req, 'form': form,
                'today': datetime.date.today().isoformat(),
            })
    return redirect('staff:test_request_detail', request_id=request_id)


@staff_required
def my_reports(request):
    reports = MedicalReport.objects.filter(uploaded_by=request.user).select_related('case', 'test_request')
    return render(request, 'staff/my_reports.html', {'reports': reports})
