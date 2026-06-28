from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        HR = "HR", "HR"
        SGM = "SGM", "Senior General Manager"
        GM = "GM", "General Manager"
        AGM = "AGM", "Assistant General Manager"
        MR = "MR", "Medical Representative"

    type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.MR,
    )

    def __str__(self):
        return f"{self.username} ({self.get_type_display()})"
