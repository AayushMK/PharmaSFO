from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import Notification
from .utils import notify


def _message_recipients(user):
    """Who this user may message: their downstream team + their manager; HR/
    superusers may message anyone active."""
    User = get_user_model()
    if user.is_superuser or (user.is_staff and user.type == "HR"):
        return User.objects.filter(is_active=True).exclude(pk=user.pk).order_by(
            "first_name", "last_name", "username"
        )
    ids = set(user.team_member_ids(include_self=False))
    if user.manager_id:
        ids.add(user.manager_id)
    return User.objects.filter(pk__in=ids, is_active=True).order_by(
        "first_name", "last_name", "username"
    )


@login_required
@never_cache
def notification_list(request):
    queryset = Notification.objects.filter(recipient=request.user)
    paginator = Paginator(queryset, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(
        request,
        "notifications/notification_list.html",
        {
            "page_obj": page_obj,
            "unread_count": queryset.filter(is_read=False).count(),
        },
    )


@require_POST
@login_required
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return redirect(notification.url or "notification_list")


@require_POST
@login_required
def mark_all_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return redirect(request.POST.get("next") or "notification_list")


@login_required
@never_cache
def send_message(request):
    recipients = _message_recipients(request.user)
    if request.method == "POST":
        recipient = recipients.filter(pk=request.POST.get("recipient")).first()
        text = (request.POST.get("message") or "").strip()
        if recipient and text:
            notify(recipient, text[:255], sender=request.user)
            messages.success(
                request, f"Message sent to {recipient.get_full_name() or recipient.username}."
            )
            return redirect("send_message")
        messages.error(request, "Pick a recipient and enter a message.")
    return render(request, "notifications/send_message.html", {"recipients": recipients})
