import calendar as cal_module
import json
from collections import defaultdict
from datetime import datetime

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from tour_plans.models import TourPlan

User = get_user_model()

SUPER_CORE_MAX = 25
CORE_MAX = 75

VISIT_TARGETS = {"super_core": 4, "core": 2, "vip": 1}
CATEGORY_LABELS = {"super_core": "Super Core", "core": "Core", "vip": "VIP"}

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _get_employee(request):
    is_staff = request.user.is_staff
    employee_id = request.GET.get("employee_id")
    if is_staff and employee_id:
        employee = get_object_or_404(User, pk=employee_id)
    else:
        employee = request.user
    all_employees = (
        User.objects.order_by("first_name", "last_name", "username") if is_staff else []
    )
    return employee, all_employees, (int(employee_id) if employee_id else None), is_staff


def _doctor_category(msl):
    if msl and 1 <= msl <= SUPER_CORE_MAX:
        return "super_core"
    if msl and SUPER_CORE_MAX < msl <= CORE_MAX:
        return "core"
    return "vip"


def _build_yearly_rows(employee, year):
    """
    Returns a list of row dicts for the yearly report, one per approved
    doctor-employee relation, ordered by MSL number then doctor name.
    Each row contains: msl, doctor, hospitals, month_visits (list of 12
    day-lists), total_calls.
    """
    relations = (
        DoctorEmployeeRelation.objects
        .filter(employee=employee, status=DoctorEmployeeRelation.Status.APPROVED)
        .select_related("doctor")
        .order_by("msl_number", "doctor__name")
    )

    all_covs = list(
        DailyCoverage.objects
        .filter(created_by=employee, report_date__year=year)
        .select_related("actual_working_place")
        .order_by("report_date")
    )

    cov_by_doctor = defaultdict(list)
    for c in all_covs:
        cov_by_doctor[c.doctor_id].append(c)

    rows = []
    for rel in relations:
        doc = rel.doctor
        covs = cov_by_doctor.get(doc.id, [])

        month_visits = []
        for m in range(1, 13):
            days = sorted({c.report_date.day for c in covs if c.report_date.month == m})
            month_visits.append(days)

        hospitals = list(dict.fromkeys(c.actual_working_place.name for c in covs))

        rows.append({
            "msl":         rel.msl_number or "-",
            "doctor":      doc,
            "hospitals":   hospitals,
            "month_visits": month_visits,
            "total_calls": len(covs),
        })

    return rows


# ── Daily Activity Report ────────────────────────────────────────────────────

@login_required
@never_cache
def daily_activity_report(request):
    employee, all_employees, selected_employee_id, is_staff = _get_employee(request)
    date_str = request.GET.get("date", "")

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
            DailyCoverage.objects
            .filter(created_by=employee, report_date=report_date)
            .select_related("doctor", "actual_working_place")
            .order_by("call_time")
        )
        coverages = list(qs)

        doctor_ids = [c.doctor_id for c in coverages]
        msl_map = {
            rel.doctor_id: rel.msl_number
            for rel in DoctorEmployeeRelation.objects.filter(
                employee=employee, doctor_id__in=doctor_ids,
            )
        }
        for c in coverages:
            c.msl = msl_map.get(c.doctor_id) or "-"

        planned_areas = list(
            TourPlan.objects
            .filter(created_by=employee, plan_date=report_date, status=TourPlan.Status.APPROVED)
            .select_related("area")
            .values_list("area__name", flat=True)
        )
        worked_areas = list(dict.fromkeys(c.actual_working_place.name for c in coverages))

    return render(request, "reports/daily_activity_report.html", {
        "date_str": date_str,
        "report_date": report_date,
        "employee": employee,
        "all_employees": all_employees,
        "selected_employee_id": selected_employee_id,
        "coverages": coverages,
        "planned_areas": planned_areas,
        "worked_areas": worked_areas,
        "is_staff": is_staff,
    })


# ── Monthly Activity Report ──────────────────────────────────────────────────

@login_required
@never_cache
def monthly_activity_report(request):
    employee, all_employees, selected_employee_id, is_staff = _get_employee(request)
    month_str = request.GET.get("month", "")

    year = month = None
    if month_str:
        try:
            dt = datetime.strptime(month_str, "%Y-%m")
            year, month = dt.year, dt.month
        except ValueError:
            pass

    if not year:
        today = datetime.today()
        year, month = today.year, today.month
        month_str = f"{year}-{month:02d}"

    num_days = cal_module.monthrange(year, month)[1]

    msl_map = {
        rel.doctor_id: rel.msl_number
        for rel in DoctorEmployeeRelation.objects.filter(employee=employee)
    }

    coverages = list(
        DailyCoverage.objects
        .filter(created_by=employee, report_date__year=year, report_date__month=month)
        .select_related("doctor", "actual_working_place")
        .order_by("report_date", "call_time")
    )
    for c in coverages:
        c.msl = msl_map.get(c.doctor_id)
        c.category = _doctor_category(c.msl)

    freq = {d: {"super_core": 0, "core": 0, "vip": 0} for d in range(1, num_days + 1)}
    for c in coverages:
        freq[c.report_date.day][c.category] += 1

    days = list(range(1, num_days + 1))
    chart_data = json.dumps({
        "labels":     days,
        "super_core": [freq[d]["super_core"] for d in days],
        "core":       [freq[d]["core"]       for d in days],
        "vip":        [freq[d]["vip"]        for d in days],
    })

    total_super_core = sum(freq[d]["super_core"] for d in days)
    total_core       = sum(freq[d]["core"]       for d in days)
    total_vip        = sum(freq[d]["vip"]        for d in days)

    all_specs = sorted({c.doctor.specialization for c in coverages if c.doctor.specialization})

    tour_by_date = defaultdict(list)
    for tp in TourPlan.objects.filter(
        created_by=employee, plan_date__year=year,
        plan_date__month=month, status=TourPlan.Status.APPROVED,
    ).select_related("area").order_by("plan_date"):
        tour_by_date[tp.plan_date].append(tp.area.name)

    cov_by_date = defaultdict(list)
    for c in coverages:
        cov_by_date[c.report_date].append(c)

    rows = []
    for d in sorted(cov_by_date):
        day_covs = cov_by_date[d]
        spec_counts = defaultdict(int)
        for c in day_covs:
            if c.doctor.specialization:
                spec_counts[c.doctor.specialization] += 1
        rows.append({
            "date":        d,
            "tour_areas":  tour_by_date.get(d, []),
            "actual_areas": list(dict.fromkeys(c.actual_working_place.name for c in day_covs)),
            "spec_values": [spec_counts.get(s, 0) for s in all_specs],
            "total_drs":   len(day_covs),
        })

    return render(request, "reports/monthly_activity_report.html", {
        "month_str":           month_str,
        "year":                year,
        "month":               month,
        "month_name":          cal_module.month_name[month],
        "employee":            employee,
        "all_employees":       all_employees,
        "selected_employee_id": selected_employee_id,
        "is_staff":            is_staff,
        "chart_data":          chart_data,
        "total_super_core":    total_super_core,
        "total_core":          total_core,
        "total_vip":           total_vip,
        "rows":                rows,
        "all_specs":           all_specs,
    })


# ── Yearly Activity Report ───────────────────────────────────────────────────

def _year_choices():
    current = datetime.today().year
    return list(range(current - 4, current + 2))


@login_required
@never_cache
def yearly_activity_report(request):
    employee, all_employees, selected_employee_id, is_staff = _get_employee(request)
    year_str = request.GET.get("year", str(datetime.today().year))
    try:
        year = int(year_str)
    except ValueError:
        year = datetime.today().year

    rows = _build_yearly_rows(employee, year)

    return render(request, "reports/yearly_activity_report.html", {
        "year":                year,
        "year_choices":        _year_choices(),
        "employee":            employee,
        "all_employees":       all_employees,
        "selected_employee_id": selected_employee_id,
        "is_staff":            is_staff,
        "rows":                rows,
        "month_abbr":          MONTH_ABBR,
    })


@login_required
def yearly_activity_report_excel(request):
    employee, _, _, _ = _get_employee(request)
    year_str = request.GET.get("year", str(datetime.today().year))
    try:
        year = int(year_str)
    except ValueError:
        year = datetime.today().year

    rows = _build_yearly_rows(employee, year)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"Yearly Report {year}"

    header_fill = PatternFill("solid", fgColor="4A90C4")
    header_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    headers = (
        ["MSL No.", "Doctor's Name", "Speciality", "Doctor NMC No.", "City", "Hospital"]
        + MONTH_ABBR
        + ["Total Calls"]
    )
    ws.append(headers)
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center

    for i, row in enumerate(rows, start=2):
        month_cells = [
            ", ".join(str(d) for d in mv) if mv else ""
            for mv in row["month_visits"]
        ]
        ws.append([
            row["msl"],
            row["doctor"].name,
            row["doctor"].specialization or "",
            row["doctor"].nmc_number,
            row["doctor"].area,
            " / ".join(row["hospitals"]),
            *month_cells,
            row["total_calls"],
        ])
        for cell in ws[i]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # Column widths
    col_widths = [8, 22, 16, 14, 12, 22] + [10] * 12 + [10]
    for col_idx, width in enumerate(col_widths, start=1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = width

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    emp_name = employee.get_full_name() or employee.username
    response["Content-Disposition"] = (
        f'attachment; filename="yearly_report_{emp_name}_{year}.xlsx"'
    )
    wb.save(response)
    return response


# ── Monthly Target Report ────────────────────────────────────────────────────

@login_required
@never_cache
def monthly_target_report(request):
    employee, all_employees, selected_employee_id, is_staff = _get_employee(request)
    month_str = request.GET.get("month", "")

    year = month = None
    if month_str:
        try:
            dt = datetime.strptime(month_str, "%Y-%m")
            year, month = dt.year, dt.month
        except ValueError:
            pass

    if not year:
        today = datetime.today()
        year, month = today.year, today.month
        month_str = f"{year}-{month:02d}"

    # All approved doctor relations ordered by MSL
    relations = (
        DoctorEmployeeRelation.objects
        .filter(employee=employee, status=DoctorEmployeeRelation.Status.APPROVED)
        .select_related("doctor")
        .order_by("msl_number", "doctor__name")
    )

    # Count visits per doctor for the month
    visit_counts = defaultdict(int)
    for cov in DailyCoverage.objects.filter(
        created_by=employee,
        report_date__year=year,
        report_date__month=month,
    ).values("doctor_id"):
        visit_counts[cov["doctor_id"]] += 1

    rows = []
    for rel in relations:
        category = _doctor_category(rel.msl_number)
        target = VISIT_TARGETS[category]
        visits = visit_counts.get(rel.doctor_id, 0)

        if visits >= target:
            state = "green"
        elif visits > 0:
            state = "orange"
        else:
            state = "red"

        rows.append({
            "state":       state,
            "doctor_name": rel.doctor.name,
            "msl":         rel.msl_number or "-",
            "visits":      visits,
            "target":      target,
            "category":    CATEGORY_LABELS[category],
        })

    return render(request, "reports/monthly_target_report.html", {
        "month_str":           month_str,
        "year":                year,
        "month":               month,
        "month_name":          cal_module.month_name[month],
        "employee":            employee,
        "all_employees":       all_employees,
        "selected_employee_id": selected_employee_id,
        "is_staff":            is_staff,
        "rows":                rows,
    })
