from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class UserType(models.TextChoices):
        # Declared in increasing order of hierarchy — TYPE_RANK derives from it.
        MSO = "MSO", "MSO"
        SR_MSO = "SR_MSO", "Sr. MSO"
        DASM = "DASM", "DASM"
        ASM = "ASM", "ASM"
        SR_ASM = "SR_ASM", "Sr. ASM"
        DRSM = "DRSM", "DRSM"
        RSM = "RSM", "RSM"
        SR_RSM = "SR_RSM", "Sr. RSM"
        DSM = "DSM", "DSM"
        SM = "SM", "SM"
        SR_SM = "SR_SM", "Sr. SM"
        AGM = "AGM", "AGM"
        GM = "GM", "GM"
        SR_GM = "SR_GM", "Sr. GM"
        HR = "HR", "HR"
        ADMIN = "ADMIN", "Admin"

    # Position -> rank; higher number = higher in the hierarchy
    TYPE_RANK = {value: rank for rank, value in enumerate(UserType.values)}

    type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.MSO,
    )

    @property
    def hierarchy_level(self):
        return self.TYPE_RANK.get(self.type, 0)

    def viewable_report_users(self):
        """Everyone whose reports this user may view: themselves plus all users
        at a strictly lower position. Superusers see everyone."""
        qs = type(self).objects.all()
        if not self.is_superuser:
            lower_types = [
                value for value, rank in self.TYPE_RANK.items()
                if rank < self.hierarchy_level
            ]
            qs = qs.filter(models.Q(pk=self.pk) | models.Q(type__in=lower_types))
        return qs.order_by("first_name", "last_name", "username")

    def __str__(self):
        return f"{self.username} ({self.get_type_display()})"
