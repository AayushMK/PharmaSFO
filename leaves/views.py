from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from notifications.utils import notify

from .forms import LeaveRequestForm
from .models import LeaveRequest


def _is_hr(user):
    return user.is_superuser or (user.is_staff and user.type == "HR")


def _can_review(reviewer, applicant):
    """A user may review leave for anyone in their downstream team, or (HR) all."""
    if reviewer.pk == applicant.pk:
        return False
    if _is_hr(reviewer):
        return True
    return applicant.pk in reviewer.team_member_ids(include_self=False)


@login_required
@never_cache
def leave_list(request):
    requests_qs = LeaveRequest.objects.filter(created_by=request.user)
    return render(request, "leaves/leave_list.html", {"requests": requests_qs})


@login_required
@never_cache
def add_leave(request):
    if request.method == "POST":
        form = LeaveRequestForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.created_by = request.user
            leave.save()
            manager = request.user.manager
            if manager:
                who = request.user.get_full_name() or request.user.username
                notify(
                    manager,
                    f"{who} requested {leave.get_leave_type_display()} leave "
                    f"({leave.start_date}–{leave.end_date}).",
                    url=reverse("leave_review"),
                )
            messages.success(request, "Leave request submitted.")
            return redirect("leave_list")
    else:
        today = timezone.localdate()
        form = LeaveRequestForm(initial={"start_date": today, "end_date": today})
    return render(request, "leaves/add_leave.html", {"form": form})


@login_required
def delete_leave(request, pk):
    leave = get_object_or_404(LeaveRequest, pk=pk, created_by=request.user)
    if leave.status != LeaveRequest.Status.PENDING:
        messages.error(request, "Only pending requests can be withdrawn.")
        return redirect("leave_list")
    if request.method == "POST":
        leave.delete()
        messages.success(request, "Leave request withdrawn.")
    return redirect("leave_list")


@login_required
@never_cache
def leave_review(request):
    user = request.user
    if _is_hr(user):
        qs = LeaveRequest.objects.exclude(created_by=user).select_related("created_by")
    else:
        team_ids = user.team_member_ids(include_self=False)
        if not team_ids:
            raise PermissionDenied
        qs = LeaveRequest.objects.filter(created_by_id__in=team_ids).select_related("created_by")

    status = request.GET.get("status", "pending")
    if status in ("pending", "approved", "rejected"):
        qs = qs.filter(status=status)
    return render(request, "leaves/leave_review.html", {"requests": qs, "status": status})


def _review_action(request, pk, new_status):
    leave = get_object_or_404(LeaveRequest, pk=pk)
    if not _can_review(request.user, leave.created_by):
        raise PermissionDenied
    if request.method == "POST":
        leave.status = new_status
        leave.reviewed_by = request.user
        leave.reviewed_at = timezone.now()
        leave.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
        verb = "approved" if new_status == LeaveRequest.Status.APPROVED else "rejected"
        notify(
            leave.created_by,
            f"Your {leave.get_leave_type_display()} leave "
            f"({leave.start_date}–{leave.end_date}) was {verb}.",
            url=reverse("leave_list"),
        )
        messages.success(request, f"Leave {verb}.")
    return redirect("leave_review")


@login_required
def approve_leave(request, pk):
    return _review_action(request, pk, LeaveRequest.Status.APPROVED)


@login_required
def reject_leave(request, pk):
    return _review_action(request, pk, LeaveRequest.Status.REJECTED)
