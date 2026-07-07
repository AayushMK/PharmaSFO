import calendar
from datetime import date, time

from django.core.management.base import BaseCommand
from django.db import transaction

from doctors.models import Doctor
from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import Area, TourPlan
from daily_coverage.models import ChemistCoverage, DailyCoverage, StockistCoverage
from users.models import User

DEMO_PASSWORD = "Demo@12345"
YEAR, MONTH = 2026, 7

AREA_NAMES = ["Kathmandu", "Lalitpur", "Bhaktapur", "Pokhara", "Biratnagar"]

DOCTORS = [
    ("Ramesh Sharma", "NMC-DEMO-1001", "Kathmandu", "Cardiology", 10),
    ("Sita Koirala", "NMC-DEMO-1002", "Kathmandu", "Pediatrics", 22),
    ("Bikash Thapa", "NMC-DEMO-1003", "Lalitpur", "Orthopedics", 40),
    ("Anita Gurung", "NMC-DEMO-1004", "Bhaktapur", "Dermatology", 65),
    ("Prakash Rai", "NMC-DEMO-1005", "Pokhara", "General Medicine", 90),
    ("Sunita Adhikari", "NMC-DEMO-1006", "Biratnagar", "Gynecology", 110),
    ("Deepak Shrestha", "NMC-DEMO-1007", "Kathmandu", "Neurology", 15),
    ("Kabita Basnet", "NMC-DEMO-1008", "Lalitpur", "ENT", 50),
]

CHEMISTS = ["Sagarmatha Pharmacy", "Everest Medical Hall", "Himal Chemist"]
STOCKISTS = ["Annapurna Distributors", "Fewa Traders"]

PRODUCTS = ["ProCard", "ProCard + NeuroMax", "OrthoFlex", "DermaCare"]


class Command(BaseCommand):
    help = "Seed dummy users (one per hierarchy type), doctors, and July 2026 activity data."

    @transaction.atomic
    def handle(self, *args, **options):
        areas = {}
        for name in AREA_NAMES:
            areas[name], _ = Area.objects.get_or_create(name=name)

        doctors = []
        for name, nmc, area, spec, msl in DOCTORS:
            doctor, _ = Doctor.objects.get_or_create(
                nmc_number=nmc,
                defaults={"name": name, "area": area, "specialization": spec},
            )
            doctors.append((doctor, msl))

        demo_usernames = [f"demo_{value.lower()}" for value in User.UserType.values]

        # Wipe previous demo data so the command is safe to re-run.
        User.objects.filter(username__in=demo_usernames).delete()

        users = []
        for user_type, label in User.UserType.choices:
            username = f"demo_{user_type.lower()}"
            user = User.objects.create_user(
                username=username,
                password=DEMO_PASSWORD,
                first_name="Demo",
                last_name=label,
                type=user_type,
                is_staff=(user_type == User.UserType.HR),
            )
            users.append(user)

        days_in_month = calendar.monthrange(YEAR, MONTH)[1]
        area_list = list(areas.values())

        for u_idx, user in enumerate(users):
            # Assign every demo doctor to every demo user with a fixed MSL number.
            relations = []
            for doctor, msl in doctors:
                rel = DoctorEmployeeRelation.objects.create(
                    employee=user,
                    doctor=doctor,
                    msl_number=msl,
                    relation_date=date(YEAR, MONTH, 1),
                    status=DoctorEmployeeRelation.Status.APPROVED,
                )
                relations.append(rel)

            for day in range(1, days_in_month + 1):
                report_date = date(YEAR, MONTH, day)
                area = area_list[(day + u_idx) % len(area_list)]

                TourPlan.objects.create(
                    created_by=user,
                    plan_date=report_date,
                    area=area,
                    remarks="Demo tour plan",
                    status=TourPlan.Status.APPROVED,
                )

                doctor = relations[(day + u_idx) % len(relations)].doctor
                DailyCoverage.objects.create(
                    created_by=user,
                    report_date=report_date,
                    doctor=doctor,
                    actual_working_place=area,
                    call_time=time(10, 0),
                    products=PRODUCTS[day % len(PRODUCTS)],
                    worked_with="",
                    remarks="Demo visit",
                )

                if day % 3 == 0:
                    ChemistCoverage.objects.create(
                        created_by=user,
                        report_date=report_date,
                        name=CHEMISTS[day % len(CHEMISTS)],
                        area=area,
                        call_time=time(14, 0),
                    )
                if day % 4 == 0:
                    StockistCoverage.objects.create(
                        created_by=user,
                        report_date=report_date,
                        name=STOCKISTS[day % len(STOCKISTS)],
                        area=area,
                        call_time=time(15, 0),
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} demo users with July {YEAR} activity. Password for all: {DEMO_PASSWORD}"
        ))
