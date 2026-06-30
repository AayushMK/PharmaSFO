import calendar
import json
from datetime import date, datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from doctors.models import Doctor
from tour_plans.models import Area, TourPlan

from .forms import DailyCoverageBulkForm, DailyCoverageForm
from .models import ChemistCoverage, DailyCoverage, StockistCoverage

EDIT_WINDOW_DAYS = 2


def _can_edit(record):
    cutoff = timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)
    return record.created_at >= cutoff


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

    days_with_entries = set(entries.values_list("report_date__day", flat=True))

    tour_plans = TourPlan.objects.filter(
        created_by=request.user,
        plan_date__year=year,
        plan_date__month=month,
    )
    days_approved = set(
        tour_plans.filter(status=TourPlan.Status.APPROVED).values_list("plan_date__day", flat=True)
    )
    days_pending = set(
        tour_plans.filter(status=TourPlan.Status.PENDING).values_list("plan_date__day", flat=True)
    )

    return render(
        request,
        "daily_coverage/calendar.html",
        {
            "year": year,
            "month": month,
            "month_name": month_name,
            "calendar": month_calendar,
            "entries": entries,
            "days_with_entries": days_with_entries,
            "days_approved": days_approved,
            "days_pending": days_pending,
            "selected_day": selected_day,
            "day_names": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        },
    )


@login_required
@never_cache
def add_daily_coverage(request, selected_date=None):
    initial_date = selected_date or request.GET.get("date") or ""

    form_error = None

    if request.method == "POST":
        form = DailyCoverageBulkForm(request.POST)
        if form.is_valid():
            doctor_entries   = form.cleaned_data.get("entries") or []
            chemist_entries  = form.cleaned_data.get("chemist_entries") or []
            stockist_entries = form.cleaned_data.get("stockist_entries") or []
            no_doctor_reason = (form.cleaned_data.get("no_doctor_reason") or "").strip()

            approved_dates = set(
                TourPlan.objects.filter(
                    created_by=request.user,
                    status=TourPlan.Status.APPROVED,
                ).values_list("plan_date", flat=True)
            )

            # Determine which dates have doctor entries being submitted
            def _parse_date(s):
                try:
                    return datetime.strptime(s, "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    return None

            submitted_doctor_dates = {
                _parse_date(e.get("report_date"))
                for e in doctor_entries
                if e.get("doctor") and e.get("report_date")
            } - {None}

            # Validate: chemist/stockist without doctor requires a reason
            chemist_dates = {_parse_date(e.get("report_date")) for e in chemist_entries if e.get("report_date")} - {None}
            stockist_dates = {_parse_date(e.get("report_date")) for e in stockist_entries if e.get("report_date")} - {None}
            non_doctor_dates = (chemist_dates | stockist_dates) - submitted_doctor_dates

            existing_doctor_dates = set(
                DailyCoverage.objects.filter(
                    created_by=request.user,
                    report_date__in=non_doctor_dates,
                ).values_list("report_date", flat=True)
            ) if non_doctor_dates else set()

            truly_missing = non_doctor_dates - existing_doctor_dates
            if truly_missing and not no_doctor_reason:
                form_error = "You must add at least one doctor entry or provide a reason for no doctor coverage."
            else:
                # Save doctor entries
                for entry in doctor_entries:
                    report_date = _parse_date(entry.get("report_date"))
                    doctor_id = entry.get("doctor")
                    actual_place_id = entry.get("actual_working_place")
                    call_time = entry.get("call_time")
                    if not report_date or not doctor_id or not actual_place_id or not call_time:
                        continue
                    if report_date not in approved_dates:
                        continue
                    DailyCoverage.objects.create(
                        created_by=request.user,
                        report_date=report_date,
                        doctor_id=doctor_id,
                        actual_working_place_id=actual_place_id,
                        call_time=call_time,
                        products=entry.get("products") or "",
                        worked_with=entry.get("worked_with") or "",
                        remarks=entry.get("remarks") or "",
                    )

                # Save chemist entries
                for entry in chemist_entries:
                    report_date = _parse_date(entry.get("report_date"))
                    name = (entry.get("name") or "").strip()
                    area_id = entry.get("area")
                    call_time = entry.get("call_time")
                    if not report_date or not name or not area_id or not call_time:
                        continue
                    if report_date not in approved_dates:
                        continue
                    ChemistCoverage.objects.create(
                        created_by=request.user,
                        report_date=report_date,
                        name=name,
                        area_id=area_id,
                        call_time=call_time,
                    )

                # Save stockist entries
                for entry in stockist_entries:
                    report_date = _parse_date(entry.get("report_date"))
                    name = (entry.get("name") or "").strip()
                    area_id = entry.get("area")
                    call_time = entry.get("call_time")
                    if not report_date or not name or not area_id or not call_time:
                        continue
                    if report_date not in approved_dates:
                        continue
                    StockistCoverage.objects.create(
                        created_by=request.user,
                        report_date=report_date,
                        name=name,
                        area_id=area_id,
                        call_time=call_time,
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
            "initial_date": initial_date,
            "form_error": form_error,
        },
    )


@login_required
@never_cache
def daily_coverage_list(request):
    filter_date_str = request.GET.get("date")
    filter_date = None
    if filter_date_str:
        try:
            filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    records = DailyCoverage.objects.filter(created_by=request.user).select_related("doctor", "actual_working_place")
    if filter_date:
        records = records.filter(report_date=filter_date)

    cutoff = timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)
    for record in records:
        record.editable = record.created_at >= cutoff

    return render(
        request,
        "daily_coverage/daily_coverage_list.html",
        {
            "records": records,
            "filter_date": filter_date,
        },
    )


@login_required
@never_cache
def edit_daily_coverage(request, pk):
    record = get_object_or_404(DailyCoverage, pk=pk, created_by=request.user)
    if not _can_edit(record):
        raise PermissionDenied

    if request.method == "POST":
        form = DailyCoverageForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            return redirect("daily_coverage_list")
    else:
        form = DailyCoverageForm(instance=record)

    return render(
        request,
        "daily_coverage/edit_daily_coverage.html",
        {"form": form, "record": record},
    )


@login_required
def delete_daily_coverage(request, pk):
    record = get_object_or_404(DailyCoverage, pk=pk, created_by=request.user)
    if not _can_edit(record):
        raise PermissionDenied

    if request.method == "POST":
        record.delete()
        return redirect("daily_coverage_list")

    return redirect("daily_coverage_list")
