import calendar
import json
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from doctors.models import Doctor
from tour_plans.models import Area

from .forms import DailyCoverageBulkForm
from .models import DailyCoverage


@login_required
@never_cache
def daily_coverage_calendar(request, year=None, month=None):
    today = date.today()
    if year is None or month is None:
        year = today.year
        month = today.month

    year = int(year)
    month = int(month)
    month_calendar = calendar.Calendar(firstweekday=0).monthdayscalendar(year, month)
    month_name = calendar.month_name[month]

    selected_date = request.GET.get("date")
    selected_day = None
    if selected_date:
        try:
            selected_day = datetime.strptime(selected_date, "%Y-%m-%d").date()
        except ValueError:
            selected_day = None

    entries = DailyCoverage.objects.filter(report_date__year=year, report_date__month=month)
    if request.user.is_authenticated:
        entries = entries.filter(created_by=request.user)

    return render(
        request,
        "daily_coverage/calendar.html",
        {
            "year": year,
            "month": month,
            "month_name": month_name,
            "calendar": month_calendar,
            "entries": entries,
            "selected_day": selected_day,
            "day_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        },
    )


@login_required
@never_cache
def add_daily_coverage(request, selected_date=None):
    if request.method == "POST":
        form = DailyCoverageBulkForm(request.POST)
        if form.is_valid():
            entries = form.cleaned_data.get("entries") or []
            for entry in entries:
                report_date = entry.get("report_date")
                doctor_id = entry.get("doctor")
                actual_place_id = entry.get("actual_working_place")
                call_time = entry.get("call_time")
                products = entry.get("products") or ""
                worked_with = entry.get("worked_with") or ""
                remarks = entry.get("remarks") or ""
                if not report_date or not doctor_id or not actual_place_id or not call_time:
                    continue
                DailyCoverage.objects.create(
                    created_by=request.user,
                    report_date=report_date,
                    doctor_id=doctor_id,
                    actual_working_place_id=actual_place_id,
                    call_time=call_time,
                    products=products,
                    worked_with=worked_with,
                    remarks=remarks,
                )
            return redirect("daily_coverage_calendar")
    else:
        form = DailyCoverageBulkForm()

    area_options = [{"value": str(area.pk), "label": area.name} for area in Area.objects.order_by("name")]
    doctor_options = [{"value": str(doctor.pk), "label": doctor.name} for doctor in Doctor.objects.order_by("name")]

    return render(
        request,
        "daily_coverage/add_daily_coverage.html",
        {
            "form": form,
            "area_options": json.dumps(area_options),
            "doctor_options": json.dumps(doctor_options),
        },
    )
