# doctor_employee_relation/models.py
from django.conf import settings
from django.db import models
from doctors.models import Doctor

class DoctorEmployeeRelation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_employee_relations",
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="doctor_employee_relations",
    )
    msl_number = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="Importance rank for this doctor for the employee",
    )
    relation_date = models.DateField(
        blank=True,
        null=True,
        help_text="Date when this doctor was assigned to the employee",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "doctor"],
                name="unique_employee_doctor_relation",
            )
        ]
        ordering = ["doctor__name"]

    def __str__(self):
        return f"{self.employee.username} -> {self.doctor.name}"