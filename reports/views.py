from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import TourPlan

User = get_user_model()


@login_required
@never_cache
def daily_activity_report(request):
    is_staff = request.user.is_staff
    date_str = request.GET.get("date", "")
    employee_id = request.GET.get("employee_id")

    if is_staff and employee_id:
        employee = get_object_or_404(User, pk=employee_id)
    else:
        employee = request.user

    all_employees = User.objects.order_by("first_name", "last_name", "username") if is_staff else []

    report_date = None
    if date_str:
        try:
            report_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    coverages = []
    planned_areas = []
    worked_areas = []

    if report_date:
        qs = (
            DailyCoverage.objects.filter(created_by=employee, report_date=report_date)
            .select_related("doctor", "actual_working_place")
            .order_by("call_time")
        )
        coverages = list(qs)

        doctor_ids = [c.doctor_id for c in coverages]
        msl_map = {
            rel.doctor_id: rel.msl_number
            for rel in DoctorEmployeeRelation.objects.filter(
                employee=employee,
                doctor_id__in=doctor_ids,
            )
        }
        for c in coverages:
            c.msl = msl_map.get(c.doctor_id) or "-"

        planned_areas = list(
            TourPlan.objects.filter(
                created_by=employee,
                plan_date=report_date,
                status=TourPlan.Status.APPROVED,
            )
            .select_related("area")
            .values_list("area__name", flat=True)
        )

        worked_areas = list(dict.fromkeys(c.actual_working_place.name for c in coverages))

    return render(
        request,
        "reports/daily_activity_report.html",
        {
            "date_str": date_str,
            "report_date": report_date,
            "employee": employee,
            "all_employees": all_employees,
            "selected_employee_id": int(employee_id) if employee_id else None,
            "coverages": coverages,
            "planned_areas": planned_areas,
            "worked_areas": worked_areas,
            "is_staff": is_staff,
        },
    )
