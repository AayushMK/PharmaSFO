import json
from datetime import datetime, timedelta

import nepali_datetime

from django.core.paginator import Paginator

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Max
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from doctors.models import Doctor
from tour_plans.models import Area, TourPlan

from .forms import (
    ChemistCoverageForm,
    ChemistForm,
    DailyCoverageBulkForm,
    DailyCoverageForm,
    StockistCoverageForm,
    StockistForm,
)
from .models import Chemist, ChemistCoverage, DailyCoverage, Stockist, StockistCoverage

EDIT_WINDOW_DAYS = 2


def _can_edit(record):
    cutoff = timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)
    return record.created_at >= cutoff


def _can_manage_directory(user):
    return user.is_authenticated and (
        user.is_superuser or (user.is_staff and user.type == "HR")
    )


def _add_partner(request, form_class, kind):
    """Shared HR view for adding a Chemist / Stockist master entry."""
    if not _can_manage_directory(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            partner = form.save()
            messages.success(request, f"{kind} “{partner.name}” added to the directory.")
            return redirect(f"add_{kind.lower()}")
    else:
        form = form_class()

    return render(request, "daily_coverage/add_partner.html", {"form": form, "kind": kind})


@login_required
@never_cache
def add_chemist(request):
    return _add_partner(request, ChemistForm, "Chemist")


@login_required
@never_cache
def add_stockist(request):
    return _add_partner(request, StockistForm, "Stockist")


@login_required
@never_cache
def daily_coverage_calendar(request, year=None, month=None):
    """Monthly coverage calendar rendered in Bikram Sambat (BS).

    `year`/`month` URL params are BS; every query and link still uses the
    Gregorian (AD) dates the data is stored in. Weeks run Sunday-first
    (Nepali work week, Saturday off).
    """
    today = timezone.localdate()
    today_bs = nepali_datetime.date.from_datetime_date(today)

    try:
        year = int(year) if year is not None else today_bs.year
        month = int(month) if month is not None else today_bs.month
        first_bs = nepali_datetime.date(year, month, 1)
    except ValueError:
        return redirect("daily_coverage_calendar")

    # prev / next BS month for calendar navigation
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    if month == 12:
        next_year, next_month = year + 1, 1
    else:
        next_year, next_month = year, month + 1

    # AD range covered by this BS month
    start_ad = first_bs.to_datetime_date()
    try:
        end_ad = nepali_datetime.date(next_year, next_month, 1).to_datetime_date() - timedelta(days=1)
    except ValueError:
        return redirect("daily_coverage_calendar")

    # {date: visit_count} — drives the "Added (n)" tag per calendar cell.
    # A day is "locked" once every entry on it is past the edit window.
    cutoff = timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)
    counts_by_date = {}
    locked_dates = set()
    for row in (
        DailyCoverage.objects.filter(
            created_by=request.user,
            report_date__range=(start_ad, end_ad),
        ).values("report_date").annotate(n=Count("id"), latest=Max("created_at"))
    ):
        counts_by_date[row["report_date"]] = row["n"]
        if row["latest"] < cutoff:
            locked_dates.add(row["report_date"])

    approved_areas = {}  # {date: area name} — approved wins if several plans share a date
    pending_dates = set()
    for plan in (
        TourPlan.objects.filter(
            created_by=request.user,
            plan_date__range=(start_ad, end_ad),
        )
        .exclude(status=TourPlan.Status.REJECTED)
        .select_related("area")
        .order_by("plan_date")
    ):
        if plan.status == TourPlan.Status.APPROVED:
            approved_areas.setdefault(plan.plan_date, plan.area.name)
        else:
            pending_dates.add(plan.plan_date)

    # Sunday-first week grid covering the BS month (adjacent-month days muted)
    grid_start = start_ad - timedelta(days=(start_ad.weekday() + 1) % 7)
    grid_end = end_ad + timedelta(days=(5 - end_ad.weekday()) % 7)
    weeks = []
    cells = []
    day = grid_start
    while day <= grid_end:
        in_month = start_ad <= day <= end_ad
        if in_month:
            bs_day = (day - start_ad).days + 1
        else:
            bs_day = nepali_datetime.date.from_datetime_date(day).day
        count = counts_by_date.get(day, 0) if in_month else 0
        if not in_month:
            state = ""
        elif count:
            state = "added"
        elif day in approved_areas:
            state = "approved"
        elif day in pending_dates:
            state = "pending"
        else:
            state = ""
        cells.append({
            "date": day,
            "bs_day": bs_day,
            "in_month": in_month,
            "count": count,
            "state": state,
            "is_today": day == today,
            "area": approved_areas.get(day, ""),
            "locked": day in locked_dates,
        })
        if len(cells) == 7:
            weeks.append(cells)
            cells = []
        day += timedelta(days=1)

    # Month summary stats (previous BS month's AD range)
    visits_month = sum(counts_by_date.values())
    try:
        prev_start_ad = nepali_datetime.date(prev_year, prev_month, 1).to_datetime_date()
        prev_month_name = nepali_datetime.date(prev_year, prev_month, 1).strftime("%B")
        prev_visits = DailyCoverage.objects.filter(
            created_by=request.user,
            report_date__range=(prev_start_ad, start_ad - timedelta(days=1)),
        ).count()
    except ValueError:
        prev_month_name = ""
        prev_visits = 0
    if prev_visits:
        delta = round((visits_month - prev_visits) * 100 / prev_visits)
        visits_trend = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        visits_delta = abs(delta)
    else:
        visits_trend = visits_delta = None

    return render(
        request,
        "daily_coverage/calendar.html",
        {
            "year": year,
            "month": month,
            "month_name": first_bs.strftime("%B"),
            "start_ad": start_ad,
            "end_ad": end_ad,
            "today_bs_label": f"{today_bs.strftime('%B')} {today_bs.day}, {today_bs.year}",
            "weeks": weeks,
            "day_names": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "prev_year": prev_year,
            "prev_month": prev_month,
            "next_year": next_year,
            "next_month": next_month,
            "days_covered": len(counts_by_date),
            "approved_days": len(approved_areas),
            "approved_not_logged": len(set(approved_areas) - set(counts_by_date)),
            "visits_month": visits_month,
            "visits_trend": visits_trend,
            "visits_delta": visits_delta,
            "prev_month_name": prev_month_name,
            "pending_count": len(pending_dates),
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
            work_day = form.cleaned_data.get("work_day") or DailyCoverage.WorkDay.FULL_DAY

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
                saved = {"doctor": 0, "chemist": 0, "stockist": 0}
                skipped_invalid = 0
                skipped_unapproved = 0

                # Save doctor entries (products and worked_with are compulsory)
                for entry in doctor_entries:
                    report_date = _parse_date(entry.get("report_date"))
                    doctor_id = entry.get("doctor")
                    actual_place_id = entry.get("actual_working_place")
                    call_time = entry.get("call_time")
                    products = (entry.get("products") or "").strip()
                    worked_with = (entry.get("worked_with") or "").strip()
                    if (not report_date or not doctor_id or not actual_place_id
                            or not call_time or not products or not worked_with):
                        skipped_invalid += 1
                        continue
                    if report_date not in approved_dates:
                        skipped_unapproved += 1
                        continue
                    saved["doctor"] += 1
                    DailyCoverage.objects.create(
                        created_by=request.user,
                        report_date=report_date,
                        work_day=work_day,
                        doctor_id=doctor_id,
                        actual_working_place_id=actual_place_id,
                        call_time=call_time,
                        products=products,
                        worked_with=worked_with,
                        remarks=entry.get("remarks") or "",
                    )

                # Save chemist entries
                for entry in chemist_entries:
                    report_date = _parse_date(entry.get("report_date"))
                    name = (entry.get("name") or "").strip()
                    area_id = entry.get("area")
                    call_time = entry.get("call_time")
                    if not report_date or not name or not area_id or not call_time:
                        skipped_invalid += 1
                        continue
                    if report_date not in approved_dates:
                        skipped_unapproved += 1
                        continue
                    saved["chemist"] += 1
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
                        skipped_invalid += 1
                        continue
                    if report_date not in approved_dates:
                        skipped_unapproved += 1
                        continue
                    saved["stockist"] += 1
                    StockistCoverage.objects.create(
                        created_by=request.user,
                        report_date=report_date,
                        name=name,
                        area_id=area_id,
                        call_time=call_time,
                    )

                total_saved = sum(saved.values())
                if total_saved:
                    parts = [f"{n} {kind}" for kind, n in saved.items() if n]
                    messages.success(request, f"Saved {total_saved} visit{'s' if total_saved != 1 else ''} ({', '.join(parts)}).")
                if skipped_unapproved:
                    messages.warning(
                        request,
                        f"{skipped_unapproved} entr{'ies' if skipped_unapproved != 1 else 'y'} skipped because there is no approved tour plan for that date.",
                    )
                if skipped_invalid:
                    messages.warning(
                        request,
                        f"{skipped_invalid} incomplete entr{'ies' if skipped_invalid != 1 else 'y'} skipped.",
                    )
                if not total_saved and not skipped_unapproved and not skipped_invalid:
                    messages.info(request, "Nothing to save. No entries were added.")
                return redirect("daily_coverage_calendar")
    else:
        form = DailyCoverageBulkForm()

    area_options = [{"value": str(area.pk), "label": area.name} for area in Area.objects.order_by("name")]
    doctor_options = [{"value": str(doctor.pk), "label": doctor.name} for doctor in Doctor.objects.order_by("name")]
    # Master directories — value is the name (coverage rows store it as text);
    # `area` lets the form pre-fill the area select for the picked partner.
    chemist_options = [
        {"value": c.name, "label": f"{c.name} ({c.area.name})", "area": str(c.area_id)}
        for c in Chemist.objects.select_related("area").order_by("name")
    ]
    stockist_options = [
        {"value": s.name, "label": f"{s.name} ({s.area.name})", "area": str(s.area_id)}
        for s in Stockist.objects.select_related("area").order_by("name")
    ]
    # "Worked with" choices — "Self" plus colleagues (stored as plain text)
    worked_with_options = [
        user.get_full_name() or user.username
        for user in get_user_model().objects.exclude(pk=request.user.pk).order_by("username")
    ]

    return render(
        request,
        "daily_coverage/add_daily_coverage.html",
        {
            "form": form,
            "area_options": json.dumps(area_options),
            "doctor_options": json.dumps(doctor_options),
            "chemist_options": json.dumps(chemist_options),
            "stockist_options": json.dumps(stockist_options),
            "worked_with_options": json.dumps(worked_with_options),
            "initial_date": initial_date,
            "form_error": form_error,
        },
    )


COVERAGE_TYPES = ("doctor", "chemist", "stockist")


@login_required
@never_cache
def daily_coverage_list(request):
    record_type = request.GET.get("type", "doctor")
    if record_type not in COVERAGE_TYPES:
        record_type = "doctor"

    filter_date_str = request.GET.get("date")
    filter_date = None
    if filter_date_str:
        try:
            filter_date = datetime.strptime(filter_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    if record_type == "doctor":
        records_qs = DailyCoverage.objects.filter(created_by=request.user).select_related("doctor", "doctor__hospital", "actual_working_place")
    elif record_type == "chemist":
        records_qs = ChemistCoverage.objects.filter(created_by=request.user).select_related("area")
    else:
        records_qs = StockistCoverage.objects.filter(created_by=request.user).select_related("area")
    if filter_date:
        records_qs = records_qs.filter(report_date=filter_date)

    paginator = Paginator(records_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    cutoff = timezone.now() - timedelta(days=EDIT_WINDOW_DAYS)
    for record in page_obj:
        record.editable = record.created_at >= cutoff

    return render(
        request,
        "daily_coverage/daily_coverage_list.html",
        {
            "page_obj": page_obj,
            "filter_date": filter_date,
            "total_count": paginator.count,
            "record_type": record_type,
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
            messages.success(request, f"Coverage record for Dr. {record.doctor.name} updated.")
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
        doctor_name = record.doctor.name
        record.delete()
        messages.success(request, f"Coverage record for Dr. {doctor_name} deleted.")
        return redirect("daily_coverage_list")

    return redirect("daily_coverage_list")


def _partner_list_url(kind):
    return f"{reverse('daily_coverage_list')}?type={kind}"


def _edit_partner_coverage(request, model, form_class, pk, kind):
    """Shared edit view for chemist/stockist coverage rows (same 2-day window)."""
    record = get_object_or_404(model, pk=pk, created_by=request.user)
    if not _can_edit(record):
        raise PermissionDenied

    if request.method == "POST":
        form = form_class(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, f"{kind.capitalize()} coverage for {record.name} updated.")
            return redirect(_partner_list_url(kind))
    else:
        form = form_class(instance=record)

    return render(
        request,
        "daily_coverage/edit_daily_coverage.html",
        {"form": form, "record": record},
    )


def _delete_partner_coverage(request, model, pk, kind):
    record = get_object_or_404(model, pk=pk, created_by=request.user)
    if not _can_edit(record):
        raise PermissionDenied

    if request.method == "POST":
        name = record.name
        record.delete()
        messages.success(request, f"{kind.capitalize()} coverage for {name} deleted.")

    return redirect(_partner_list_url(kind))


@login_required
@never_cache
def edit_chemist_coverage(request, pk):
    return _edit_partner_coverage(request, ChemistCoverage, ChemistCoverageForm, pk, "chemist")


@login_required
def delete_chemist_coverage(request, pk):
    return _delete_partner_coverage(request, ChemistCoverage, pk, "chemist")


@login_required
@never_cache
def edit_stockist_coverage(request, pk):
    return _edit_partner_coverage(request, StockistCoverage, StockistCoverageForm, pk, "stockist")


@login_required
def delete_stockist_coverage(request, pk):
    return _delete_partner_coverage(request, StockistCoverage, pk, "stockist")
