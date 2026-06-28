from django.conf import settings
from django.db import models

from doctors.models import Doctor
from tour_plans.models import Area


class DailyCoverage(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_coverages",
        null=True,
        blank=True,
    )
    report_date = models.DateField()
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="daily_coverages")
    actual_working_place = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="daily_coverage_places")
    call_time = models.TimeField()
    products = models.CharField(max_length=255, blank=True)
    worked_with = models.CharField(max_length=255, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.report_date} - {self.doctor}"
