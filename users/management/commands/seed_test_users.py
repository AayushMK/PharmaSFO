"""Seed a small, representative set of TEST users + activity for manual testing.

Every account username is prefixed `test_` so the whole set is trivial to
remove later (deleting the users cascades their tour plans, coverage, and
doctor assignments). Idempotent — re-running rebuilds the same set cleanly.

Scenarios covered:
  - A reporting chain (SM → RSM → ASM → two MSOs) to exercise Teams + the
    team-scoped report visibility.
  - An HR user (is_staff), an unassigned MSO (visible only to HR), and a
    deactivated MSO.
  - Doctor assignments with varied MSL (Super Core / Core / VIP), some
    approved and some pending (HR doctor-request queue).
  - An approved tour plan (today) + a pending one (HR tour-plan queue).
  - Daily coverage rows on the approved day so reports show data.

Usage (local, or against Heroku via DATABASE_URL):
    python manage.py seed_test_users
    docker compose run --rm -e DATABASE_URL="$HEROKU_DB_URL" web \
        uv run python manage.py seed_test_users
"""

from datetime import time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from doctors.models import Doctor
from tour_plans.models import Area, TourPlan
from users.models import User

PASSWORD = "Test@12345"
PREFIX = "test_"

# username -> (first_name, position, manager_username, is_active, is_staff)
USERS = [
    ("test_sm",         "Sam",     User.UserType.SM,  None,          True,  False),
    ("test_rsm",        "Rita",    User.UserType.RSM, "test_sm",     True,  False),
    ("test_asm",        "Amit",    User.UserType.ASM, "test_rsm",    True,  False),
    ("test_mso1",       "Manish",  User.UserType.MSO, "test_asm",    True,  False),
    ("test_mso2",       "Mina",    User.UserType.MSO, "test_asm",    True,  False),
    ("test_hr",         "Hari",    User.UserType.HR,  None,          True,  True),
    ("test_unassigned", "Ujwal",   User.UserType.MSO, None,          True,  False),
    ("test_inactive",   "Ishan",   User.UserType.MSO, "test_asm",    False, False),
]


class Command(BaseCommand):
    help = "Seed representative test users + sample activity (all prefixed test_)."

    @transaction.atomic
    def handle(self, *args, **opts):
        # 1) Users (idempotent by username).
        users = {}
        for uname, first, utype, _mgr, is_active, is_staff in USERS:
            u, _ = User.objects.update_or_create(
                username=uname,
                defaults={
                    "first_name": first,
                    "last_name": "Test",
                    "type": utype,
                    "is_active": is_active,
                    "is_staff": is_staff,
                },
            )
            u.set_password(PASSWORD)
            u.save()
            users[uname] = u

        # 2) Reporting chain (manager FKs) — second pass, now all exist.
        for uname, _first, _utype, mgr, _active, _staff in USERS:
            u = users[uname]
            u.manager = users.get(mgr) if mgr else None
            u.save(update_fields=["manager"])

        test_users = list(users.values())

        # 3) Clear this test set's prior activity so the seed is repeatable.
        DailyCoverage.objects.filter(created_by__in=test_users).delete()
        TourPlan.objects.filter(created_by__in=test_users).delete()
        DoctorEmployeeRelation.objects.filter(employee__in=test_users).delete()

        area, _ = Area.objects.get_or_create(name="Kathmandu")
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        doctors = list(Doctor.objects.order_by("id")[:5])
        made = {"relations": 0, "tour_plans": 0, "coverage": 0}

        if len(doctors) >= 4:
            mso1, mso2, asm = users["test_mso1"], users["test_mso2"], users["test_asm"]

            # 4) Doctor assignments — varied MSL → Super Core / Core / VIP.
            approved_for_mso1 = [
                (doctors[0], 10),   # Super Core (1–25)
                (doctors[1], 50),   # Core (26–75)
                (doctors[2], 100),  # VIP (76+)
            ]
            for doc, msl in approved_for_mso1:
                DoctorEmployeeRelation.objects.create(
                    employee=mso1, doctor=doc, msl_number=msl,
                    relation_date=today, status=DoctorEmployeeRelation.Status.APPROVED,
                )
                made["relations"] += 1
            # Pending requests → HR doctor-request queue.
            DoctorEmployeeRelation.objects.create(
                employee=mso1, doctor=doctors[3], msl_number=30,
                relation_date=today, status=DoctorEmployeeRelation.Status.PENDING,
            )
            DoctorEmployeeRelation.objects.create(
                employee=mso2, doctor=doctors[0], msl_number=15,
                relation_date=today, status=DoctorEmployeeRelation.Status.PENDING,
            )
            made["relations"] += 2

            # 5) Tour plans — approved (today) enables coverage; pending → HR queue.
            TourPlan.objects.create(
                created_by=mso1, plan_date=today, area=area, worked_with=asm,
                remarks="Test approved plan", status=TourPlan.Status.APPROVED,
            )
            TourPlan.objects.create(
                created_by=mso1, plan_date=tomorrow, area=area,
                remarks="Test pending plan", status=TourPlan.Status.PENDING,
            )
            TourPlan.objects.create(
                created_by=mso2, plan_date=tomorrow, area=area,
                remarks="Test pending plan (mso2)", status=TourPlan.Status.PENDING,
            )
            made["tour_plans"] += 3

            # 6) Daily coverage on the approved day → reports have data.
            for doc, t in zip(doctors[:3], [time(10, 0), time(11, 30), time(14, 15)]):
                DailyCoverage.objects.create(
                    created_by=mso1, report_date=today,
                    work_day=DailyCoverage.WorkDay.FULL_DAY,
                    doctor=doc, actual_working_place=area, call_time=t,
                    products="TestProduct 500", worked_with="Self",
                    remarks="Test coverage",
                )
                made["coverage"] += 1

        self.stdout.write(self.style.MIGRATE_HEADING("\nSeeded test users:"))
        for uname, first, utype, mgr, is_active, is_staff in USERS:
            tags = []
            if is_staff:
                tags.append("HR/staff")
            if not is_active:
                tags.append("DEACTIVATED")
            if mgr is None and not is_staff:
                tags.append("no manager")
            note = f"  ({', '.join(tags)})" if tags else ""
            self.stdout.write(f"  {uname:16} {User.UserType(utype).label:8} reports_to={mgr or '—'}{note}")

        self.stdout.write(self.style.MIGRATE_HEADING("\nSample activity:"))
        self.stdout.write(f"  doctor assignments: {made['relations']}  (3 approved for test_mso1, 2 pending)")
        self.stdout.write(f"  tour plans:         {made['tour_plans']}  (1 approved today, 2 pending)")
        self.stdout.write(f"  daily coverage:     {made['coverage']}  (test_mso1, today)")
        if not doctors:
            self.stdout.write(self.style.WARNING("  No doctors in DB — activity skipped. Import doctors first."))
        self.stdout.write(self.style.SUCCESS(f"\n  All accounts share password: {PASSWORD}"))
        self.stdout.write(self.style.SUCCESS("  done."))
