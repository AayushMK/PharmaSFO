"""Remove all seeded TEST users (username prefix `test_`) and their activity.

Deleting the users cascades their tour plans, daily coverage, and doctor
assignments (all FK on_delete=CASCADE), so this fully tears down whatever
`seed_test_users` created. Superusers are never touched.

Usage (local, or against Heroku via DATABASE_URL):
    python manage.py delete_test_users --dry-run
    python manage.py delete_test_users
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import TourPlan
from users.models import User

PREFIX = "test_"


class Command(BaseCommand):
    help = "Delete all test_ users and their seeded activity (cascade)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted, then roll back")

    def handle(self, *args, **opts):
        dry_run = opts["dry_run"]
        with transaction.atomic():
            users = User.objects.filter(username__startswith=PREFIX, is_superuser=False)
            n_users = users.count()
            n_tp = TourPlan.objects.filter(created_by__in=users).count()
            n_cov = DailyCoverage.objects.filter(created_by__in=users).count()
            n_rel = DoctorEmployeeRelation.objects.filter(employee__in=users).count()
            names = sorted(users.values_list("username", flat=True))

            users.delete()  # cascades tour plans, coverage, assignments
            if dry_run:
                transaction.set_rollback(True)

        header = "Would delete (DRY RUN — rolled back)" if dry_run else "Deleted"
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{header}:"))
        self.stdout.write(f"  test users:          {n_users}  {names}")
        self.stdout.write(f"  tour plans:          {n_tp}")
        self.stdout.write(f"  daily coverage:      {n_cov}")
        self.stdout.write(f"  doctor assignments:  {n_rel}")
        self.stdout.write(self.style.SUCCESS("\n  done."))
