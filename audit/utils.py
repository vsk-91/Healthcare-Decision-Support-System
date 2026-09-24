import logging
from .models import AuditLog

logger = logging.getLogger(__name__)


def log_action(user, action, description, request=None, extra_data=None):
    try:
        ip = None
        if request:
            x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded:
                raw_ip = x_forwarded.split(',')[0].strip()
            else:
                raw_ip = request.META.get('REMOTE_ADDR')
            if raw_ip:
                # If raw_ip has a port (e.g. 1.2.3.4:5678), strip it
                if ':' in raw_ip and not raw_ip.startswith('['):
                    # Check if IPv4 with port or IPv6
                    parts = raw_ip.split(':')
                    if len(parts) == 2:
                        raw_ip = parts[0]
                ip = raw_ip
        AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip,
        )
    except Exception as exc:
        logger.warning("Failed to record audit log: %s", exc)

