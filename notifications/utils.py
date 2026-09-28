from .models import Notification


def notify(recipients, message, url="", sender=None):
    """Create a notification for one user or an iterable of users.

    `sender` marks a person-to-person message (shown as "From: X"); leave it
    None for system notifications.
    """
    if hasattr(recipients, "pk"):
        recipients = [recipients]
    Notification.objects.bulk_create(
        Notification(recipient=user, message=message, url=url, sender=sender)
        for user in recipients
    )
