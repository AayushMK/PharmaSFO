from django.db import models

from tour_plans.models import Area


class Hospital(models.Model):
    name = models.CharField(max_length=255)
    area = models.ForeignKey(Area, on_delete=models.PROTECT, related_name="hospitals")
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "area"], name="unique_hospital_name_area"),
        ]

    def __str__(self):
        return f"{self.name} ({self.area.name})"


class Doctor(models.Model):
    name = models.CharField(max_length=255)
    nmc_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nepal Medical Council Number",
    )
    hospital = models.ForeignKey(
        Hospital, on_delete=models.PROTECT, related_name="doctors"
    )
    # Secondary hospital/area free text (col G of the MSL universe import); the
    # primary hospital is the normalized `hospital` FK above.
    second_hospital = models.CharField(max_length=255, blank=True)
    area = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"Dr. {self.name} (NMC: {self.nmc_number})"
