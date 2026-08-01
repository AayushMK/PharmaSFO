from collections import defaultdict

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

    # Reporting chain: each employee reports to exactly one higher-position
    # manager; a manager can have many direct reports (their "team"). HR assigns
    # this on the Team management page. SET_NULL so removing a manager leaves
    # their reports temporarily unassigned rather than deleting anyone.
    manager = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="team_members",
        help_text="Direct manager this employee reports to (a higher position).",
    )

    @property
    def hierarchy_level(self):
        return self.TYPE_RANK.get(self.type, 0)

    def team_member_ids(self, include_self=True):
        """PKs of this user's entire downstream reporting team.

        Walks the manager tree downward — direct reports, their reports, and so
        on — so a higher-up's "team" is every employee beneath them in the
        reporting chain. Used to scope report visibility.
        """
        edges = (
            type(self).objects
            .exclude(manager__isnull=True)
            .values_list("pk", "manager_id")
        )
        children = defaultdict(list)
        for uid, manager_id in edges:
            children[manager_id].append(uid)

        ids = {self.pk} if include_self else set()
        stack = list(children[self.pk])
        while stack:
            uid = stack.pop()
            if uid in ids:
                continue
            ids.add(uid)
            stack.extend(children[uid])
        return ids

    def viewable_report_users(self):
        """Everyone whose reports this user may view.

        HR and superusers see every employee. Everyone else sees themselves plus
        their entire downstream reporting team (direct and indirect reports via
        the `manager` chain). Employees not assigned under anyone are therefore
        visible only to HR/superusers.
        """
        qs = type(self).objects.all()
        if not (self.is_superuser or self.type == self.UserType.HR):
            qs = qs.filter(pk__in=self.team_member_ids(include_self=True))
        return qs.order_by("first_name", "last_name", "username")

    def __str__(self):
        return f"{self.username} ({self.get_type_display()})"
