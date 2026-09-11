from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(role_check_func, redirect_url='accounts:login', error_msg='Access denied.'):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(redirect_url)
            if not role_check_func(request.user):
                messages.error(request, error_msg)
                return redirect(redirect_url)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

patient_required = role_required(lambda u: u.is_patient, error_msg='Patient area only.')
doctor_required = role_required(lambda u: u.is_doctor, error_msg='Doctor area only.')
staff_required = role_required(lambda u: u.is_staff_member, error_msg='Staff area only.')
admin_required = role_required(lambda u: u.is_administrator or u.is_superuser, error_msg='Admin area only.')
