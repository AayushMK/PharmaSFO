from django.conf import settings
from django.db import models

from doctors.models import Doctor
from tour_plans.models import Area


class Chemist(models.Model):
    """Master directory of chemists (pharmacies). Coverage rows still store the
    name as free text; this table backs admin/master data and future pickers."""
    name = models.CharField(max_length=255)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="chemists")
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "area"], name="unique_chemist_name_area"),
        ]

    def __str__(self):
        return f"{self.name} ({self.area.name})"


class Stockist(models.Model):
    """Master directory of stockists (distributors). Same role as Chemist."""
    name = models.CharField(max_length=255)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="stockists")
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "area"], name="unique_stockist_name_area"),
        ]

    def __str__(self):
        return f"{self.name} ({self.area.name})"


class ChemistCoverage(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chemist_coverages",
        null=True,
        blank=True,
    )
    report_date = models.DateField()
    name = models.CharField(max_length=255)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="chemist_coverage_places")
    call_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.report_date} - {self.name}"


class StockistCoverage(models.Model):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stockist_coverages",
        null=True,
        blank=True,
    )
    report_date = models.DateField()
    name = models.CharField(max_length=255)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="stockist_coverage_places")
    call_time = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-report_date", "-created_at"]

    def __str__(self):
        return f"{self.report_date} - {self.name}"


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
