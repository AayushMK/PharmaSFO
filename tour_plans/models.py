from django.conf import settings
from django.db import models


class Area(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TourPlan(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tour_plans",
        null=True,
        blank=True,
    )
    reporting_date = models.DateField(auto_now_add=True)
    plan_date = models.DateField()
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="tour_plans")
    worked_with = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tour_plans_worked_with",
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-plan_date", "-created_at"]

    def __str__(self):
        return f"{self.plan_date} - {self.area}"
