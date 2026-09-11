from .models import AuditLog


def log_action(user, action, description, request=None, extra_data=None):
    ip = None
    if request:
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded.split(',')[0].strip() if x_forwarded else request.META.get('REMOTE_ADDR')
    AuditLog.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=ip,
    )
