from datetime import date, time, timedelta

import nepali_datetime
from django.core.management.base import BaseCommand
from django.db import transaction

from doctors.models import Doctor, Hospital
from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import Area, TourPlan
from daily_coverage.models import Chemist, ChemistCoverage, DailyCoverage, Stockist, StockistCoverage
from users.models import User

DEMO_PASSWORD = "Demo@12345"

BS_MONTH_NAMES = ["", "Baishakh", "Jestha", "Asar", "Shrawan", "Bhadau", "Aswin",
                  "Kartik", "Mangsir", "Poush", "Magh", "Falgun", "Chaitra"]


def _bs_seed_range():
    """AD range spanning the previous + current BS months, so the BS calendar
    and reports show fully-covered Nepali months. Dates stay Gregorian in the
    DB — only the *span* is aligned to BS."""
    today_bs = nepali_datetime.date.from_datetime_date(date.today())
    if today_bs.month == 1:
        prev_y, prev_m = today_bs.year - 1, 12
    else:
        prev_y, prev_m = today_bs.year, today_bs.month - 1
    if today_bs.month == 12:
        next_y, next_m = today_bs.year + 1, 1
    else:
        next_y, next_m = today_bs.year, today_bs.month + 1
    start = nepali_datetime.date(prev_y, prev_m, 1).to_datetime_date()
    end = nepali_datetime.date(next_y, next_m, 1).to_datetime_date() - timedelta(days=1)
    label = (f"{BS_MONTH_NAMES[prev_m]}–{BS_MONTH_NAMES[today_bs.month]} "
             f"{today_bs.year} BS")
    return start, end, label

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
    help = "Seed dummy users (one per hierarchy type), doctors, and activity spanning the previous + current BS months."

    @transaction.atomic
    def handle(self, *args, **options):
        areas = {}
        for name in AREA_NAMES:
            areas[name], _ = Area.objects.get_or_create(name=name)

        hospitals = {}
        for name in AREA_NAMES:
            hospitals[name], _ = Hospital.objects.get_or_create(
                name=f"{name} General Hospital", area=areas[name],
            )

        # Chemist / stockist master directories
        for i, name in enumerate(CHEMISTS):
            Chemist.objects.get_or_create(name=name, area=areas[AREA_NAMES[i % len(AREA_NAMES)]])
        for i, name in enumerate(STOCKISTS):
            Stockist.objects.get_or_create(name=name, area=areas[AREA_NAMES[i % len(AREA_NAMES)]])

        doctors = []
        for name, nmc, area, spec, msl in DOCTORS:
            doctor, _ = Doctor.objects.get_or_create(
                nmc_number=nmc,
                defaults={
                    "name": name,
                    "area": area,
                    "specialization": spec,
                    "hospital": hospitals[area],
                },
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

        start_ad, end_ad, bs_label = _bs_seed_range()
        day_count = (end_ad - start_ad).days + 1
        area_list = list(areas.values())

        for u_idx, user in enumerate(users):
            # Assign every demo doctor to every demo user with a fixed MSL number.
            relations = []
            for doctor, msl in doctors:
                rel = DoctorEmployeeRelation.objects.create(
                    employee=user,
                    doctor=doctor,
                    msl_number=msl,
                    relation_date=start_ad,
                    status=DoctorEmployeeRelation.Status.APPROVED,
                )
                relations.append(rel)

            for offset in range(day_count):
                report_date = start_ad + timedelta(days=offset)
                idx = offset + 1
                area = area_list[(idx + u_idx) % len(area_list)]

                TourPlan.objects.create(
                    created_by=user,
                    plan_date=report_date,
                    area=area,
                    remarks="Demo tour plan",
                    status=TourPlan.Status.APPROVED,
                )

                doctor = relations[(idx + u_idx) % len(relations)].doctor
                DailyCoverage.objects.create(
                    created_by=user,
                    report_date=report_date,
                    doctor=doctor,
                    actual_working_place=area,
                    call_time=time(10, 0),
                    products=PRODUCTS[idx % len(PRODUCTS)],
                    worked_with="",
                    remarks="Demo visit",
                )

                if idx % 3 == 0:
                    ChemistCoverage.objects.create(
                        created_by=user,
                        report_date=report_date,
                        name=CHEMISTS[idx % len(CHEMISTS)],
                        area=area,
                        call_time=time(14, 0),
                    )
                if idx % 4 == 0:
                    StockistCoverage.objects.create(
                        created_by=user,
                        report_date=report_date,
                        name=STOCKISTS[idx % len(STOCKISTS)],
                        area=area,
                        call_time=time(15, 0),
                    )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(users)} demo users with activity {start_ad} – {end_ad} AD "
            f"({bs_label}). Password for all: {DEMO_PASSWORD}"
        ))
