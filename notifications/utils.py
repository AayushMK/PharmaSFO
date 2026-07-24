from .models import Notification


def notify(recipients, message, url=""):
    """Create a notification for one user or an iterable of users."""
    if hasattr(recipients, "pk"):
        recipients = [recipients]
    Notification.objects.bulk_create(
        Notification(recipient=user, message=message, url=url) for user in recipients
    )
