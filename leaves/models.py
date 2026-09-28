from django.conf import settings
from django.db import models


class LeaveRequest(models.Model):
    """An employee's leave application, approved by their manager (or HR).

    Approval mirrors the tour-plan pattern: reviewer must be the applicant's
    manager (anyone in their upward chain) or HR/superuser."""

    class LeaveType(models.TextChoices):
        SICK = "sick", "Sick"
        CASUAL = "casual", "Casual"
        ANNUAL = "annual", "Annual"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="leave_requests"
    )
    leave_type = models.CharField(max_length=20, choices=LeaveType.choices, default=LeaveType.CASUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_leaves",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]

    @property
    def days(self):
        return (self.end_date - self.start_date).days + 1

    def __str__(self):
        return f"{self.created_by} · {self.get_leave_type_display()} · {self.start_date}–{self.end_date}"
