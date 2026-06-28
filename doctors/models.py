from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=255)
    nmc_number = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Nepal Medical Council Number",
    )
    area = models.CharField(max_length=255)
    specialization = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"Dr. {self.name} (NMC: {self.nmc_number})"
