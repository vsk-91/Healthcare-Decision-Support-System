import json
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from accounts.models import User, DoctorProfile, StaffProfile
from datasets.models import Dataset
from ai_engine.models import AIModel, AIAnalysis
from cases.models import PatientCase
from audit.models import AuditLog
from accounts.forms import (
    AdminUserForm, CreateDoctorForm, CreateStaffForm, ResetPasswordForm,
)
from datasets.forms import DatasetUploadForm
from ai_engine.forms import AIModelForm
from accounts.decorators import admin_required
from audit.utils import log_action


# ─────────────────────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────────────────────

@admin_required
def dashboard(request):
    from django.db.models import Count
    status_qs = PatientCase.objects.values('status').annotate(count=Count('id'))
    status_map = {s['status']: s['count'] for s in status_qs}
    chart_labels = [label for _, label in PatientCase.STATUS_CHOICES]
    chart_data   = [status_map.get(s, 0) for s, _ in PatientCase.STATUS_CHOICES]
    context = {
        'total_users':     User.objects.count(),
        'total_patients':  User.objects.filter(role=User.ROLE_PATIENT).count(),
        'total_doctors':   User.objects.filter(role=User.ROLE_DOCTOR).count(),
        'total_staff':     User.objects.filter(role=User.ROLE_STAFF).count(),
        'total_cases':     PatientCase.objects.count(),
        'pending_cases':   PatientCase.objects.exclude(status=PatientCase.STATUS_COMPLETED).count(),
        'completed_cases': PatientCase.objects.filter(status=PatientCase.STATUS_COMPLETED).count(),
        'ai_analyses':     AIAnalysis.objects.count(),
        'recent_logs':     AuditLog.objects.all()[:8],
        'chart_labels':    json.dumps(chart_labels),
        'chart_data':      json.dumps(chart_data),
    }
    return render(request, 'admin_panel/dashboard.html', context)


# ─────────────────────────────────────────────────────────────
# USER LIST
# ─────────────────────────────────────────────────────────────

@admin_required
def user_list(request):
    role = request.GET.get('role', '')
    users = User.objects.all().order_by('-date_joined')
    if role:
        users = users.filter(role=role)
    paginator = Paginator(users, 20)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/users.html', {
        'users':        page,
        'role_filter':  role,
        'role_choices': User.ROLE_CHOICES,
    })


# ─────────────────────────────────────────────────────────────
# GENERIC USER CREATE  (admin edit of basic fields — no password)
# ─────────────────────────────────────────────────────────────

@admin_required
def user_create(request):
    form = AdminUserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        log_action(request.user, 'USER_CREATE',
                   f'Created user: {user.username} (role: {user.role})', request)
        messages.success(request, f'User "{user.username}" created successfully.')
        return redirect('administration:user_list')
    return render(request, 'admin_panel/user_form.html', {'form': form, 'action': 'Create'})


# ─────────────────────────────────────────────────────────────
# CREATE DOCTOR  (Admin-only — sets role=DOCTOR + DoctorProfile)
# ─────────────────────────────────────────────────────────────

@admin_required
def create_doctor(request):
    form = CreateDoctorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        doctor = form.save()
        log_action(request.user, 'USER_CREATE',
                   f'Admin created Doctor account: {doctor.username} '
                   f'({doctor.first_name} {doctor.last_name})', request)
        messages.success(
            request,
            f'Doctor account created successfully. '
            f'Username: {doctor.username} | '
            f'Name: Dr. {doctor.first_name} {doctor.last_name}'
        )
        return redirect('administration:user_list')
    return render(request, 'admin_panel/create_doctor.html', {
        'form': form,
        'page_title': 'Create Doctor Account',
    })


# ─────────────────────────────────────────────────────────────
# CREATE STAFF  (Admin-only — sets role=STAFF + StaffProfile)
# ─────────────────────────────────────────────────────────────

@admin_required
def create_staff(request):
    form = CreateStaffForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        staff_user = form.save()
        log_action(request.user, 'USER_CREATE',
                   f'Admin created Staff account: {staff_user.username} '
                   f'({staff_user.first_name} {staff_user.last_name})', request)
        messages.success(
            request,
            f'Staff account created successfully. '
            f'Username: {staff_user.username} | '
            f'Name: {staff_user.first_name} {staff_user.last_name}'
        )
        return redirect('administration:user_list')
    return render(request, 'admin_panel/create_staff.html', {
        'form': form,
        'page_title': 'Create Staff Account',
    })


# ─────────────────────────────────────────────────────────────
# USER EDIT
# ─────────────────────────────────────────────────────────────

@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    form = AdminUserForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request.user, 'USER_EDIT',
                   f'Edited user: {user.username}', request)
        messages.success(request, f'User "{user.username}" updated successfully.')
        return redirect('administration:user_list')
    return render(request, 'admin_panel/user_form.html', {
        'form': form, 'action': 'Edit', 'edit_user': user,
    })


# ─────────────────────────────────────────────────────────────
# TOGGLE ACTIVE / INACTIVE
# ─────────────────────────────────────────────────────────────

@admin_required
def user_toggle(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        # Protect: cannot deactivate self
        if user.pk == request.user.pk:
            messages.error(request, 'You cannot deactivate your own account.')
            return redirect('administration:user_list')
        user.is_active = not user.is_active
        user.save()
        action = 'enabled' if user.is_active else 'disabled'
        log_action(request.user, 'USER_DISABLE',
                   f'User {user.username} {action}', request)
        messages.success(
            request,
            f'Account "{user.username}" has been {"activated" if user.is_active else "deactivated"}.'
        )
    return redirect('administration:user_list')


# ─────────────────────────────────────────────────────────────
# RESET PASSWORD (Admin resets any user's password)
# ─────────────────────────────────────────────────────────────

@admin_required
def user_reset_password(request, user_id):
    target = get_object_or_404(User, id=user_id)
    form   = ResetPasswordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        target.set_password(form.cleaned_data['new_password'])
        target.save()
        log_action(request.user, 'USER_EDIT',
                   f'Admin reset password for user: {target.username}', request)
        messages.success(
            request,
            f'Password for "{target.username}" has been reset successfully.'
        )
        return redirect('administration:user_list')
    return render(request, 'admin_panel/reset_password.html', {
        'form': form,
        'target_user': target,
    })


# ─────────────────────────────────────────────────────────────
# USER DETAIL  (view profile)
# ─────────────────────────────────────────────────────────────

@admin_required
def user_detail(request, user_id):
    target = get_object_or_404(User, id=user_id)
    doctor_profile = getattr(target, 'doctor_profile', None)
    staff_profile  = getattr(target, 'staff_profile', None)
    patient_profile = getattr(target, 'patient_profile', None)
    return render(request, 'admin_panel/user_detail.html', {
        'target_user':    target,
        'doctor_profile': doctor_profile,
        'staff_profile':  staff_profile,
        'patient_profile': patient_profile,
    })


# ─────────────────────────────────────────────────────────────
# DATASETS
# ─────────────────────────────────────────────────────────────

@admin_required
def dataset_list(request):
    datasets = Dataset.objects.all().order_by('-id')
    form = DatasetUploadForm()
    return render(request, 'admin_panel/datasets.html', {'datasets': datasets, 'form': form})


@admin_required
def dataset_upload(request):
    form = DatasetUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        ds = form.save(commit=False)
        ds.uploaded_by = request.user
        ds.save()
        log_action(request.user, 'DATASET_UPLOAD',
                   f'Uploaded dataset: {ds.name}', request)
        return redirect('administration:dataset_list')
    return render(request, 'admin_panel/dataset_form.html', {'form': form})


@admin_required
def dataset_delete(request, dataset_id):
    if request.method == 'POST':
        ds = get_object_or_404(Dataset, id=dataset_id)
        name = ds.name
        ds.delete()
        log_action(request.user, 'SYSTEM', f'Deleted dataset: {name}', request)
    return redirect('administration:dataset_list')


# ─────────────────────────────────────────────────────────────
# AI MODELS
# ─────────────────────────────────────────────────────────────

@admin_required
def ai_model_list(request):
    models = AIModel.objects.all().order_by('-id')
    form = AIModelForm()
    return render(request, 'admin_panel/ai_models.html', {'models': models, 'form': form})


@admin_required
def ai_model_create(request):
    form = AIModelForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        model = form.save(commit=False)
        model.created_by = request.user
        model.save()
        log_action(request.user, 'SYSTEM',
                   f'Registered AI model: {model.name} v{model.version}', request)
        return redirect('administration:ai_model_list')
    return render(request, 'admin_panel/model_form.html', {'form': form})


@admin_required
def ai_model_train(request, model_id):
    model = get_object_or_404(AIModel, id=model_id)
    if request.method == 'POST':
        from django.utils import timezone
        model.status     = AIModel.STATUS_ACTIVE
        model.accuracy   = 0.87
        model.precision  = 0.85
        model.recall     = 0.83
        model.f1_score   = 0.84
        model.trained_at = timezone.now()
        model.save()
        log_action(request.user, 'MODEL_TRAIN',
                   f'Mock training completed for model: {model.name} v{model.version}', request)
    return redirect('administration:ai_model_list')


# ─────────────────────────────────────────────────────────────
# AUDIT LOGS
# ─────────────────────────────────────────────────────────────

@admin_required
def audit_log_list(request):
    logs = AuditLog.objects.order_by('-timestamp')
    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)
    action_choices = AuditLog.objects.values_list('action', flat=True).distinct().order_by('action')
    paginator = Paginator(logs, 30)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'admin_panel/audit_logs.html', {
        'logs':           page,
        'action_filter':  action_filter,
        'action_choices': [(a, a.replace('_', ' ').title()) for a in action_choices],
    })


# ─────────────────────────────────────────────────────────────
# ALL CASES
# ─────────────────────────────────────────────────────────────

@admin_required
def case_list(request):
    cases = PatientCase.objects.all().select_related(
        'patient', 'assigned_doctor'
    ).order_by('-created_at')
    return render(request, 'admin_panel/cases.html', {'cases': cases})
