from .models import Notification

RECENT_LIMIT = 8


def unread_count(request):
    """Unread count + most recent notifications for the topbar bell dropdown
    (rendered on every authenticated page from base.html)."""
    user = getattr(request, "user", None)
    if not (user and user.is_authenticated):
        return {}
    own = Notification.objects.filter(recipient=user)
    return {
        "unread_notification_count": own.filter(is_read=False).count(),
        "recent_notifications": own[:RECENT_LIMIT],
    }
