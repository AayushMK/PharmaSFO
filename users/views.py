import calendar
from collections import defaultdict
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from daily_coverage.models import ChemistCoverage, DailyCoverage, StockistCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from reports.views import CATEGORY_LABELS, VISIT_TARGETS, _doctor_category
from tour_plans.models import TourPlan

from .forms import UserCreateForm, UserEditForm
from .models import User


def _can_manage_users(user):
    return user.is_authenticated and (
        user.is_superuser or (user.is_staff and user.type == "HR")
    )


@login_required
@never_cache
def add_user(request):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            messages.success(
                request,
                f"{new_user.get_full_name() or new_user.username} "
                f"({new_user.get_type_display()}) added. They can log in now.",
            )
            return redirect("user_list")
    else:
        form = UserCreateForm()

    return render(request, "users/add_user.html", {"form": form})


@login_required
@never_cache
def user_list(request):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    employees = User.objects.all().order_by("first_name", "last_name", "username")
    return render(request, "users/user_list.html", {"employees": employees})


@login_required
@never_cache
def edit_user(request, pk):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    employee = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserEditForm(request.POST, instance=employee)
        if form.is_valid():
            form.save()
            messages.success(request, f"{employee.get_full_name() or employee.username} updated.")
            return redirect("user_list")
    else:
        form = UserEditForm(instance=employee)

    return render(request, "users/edit_user.html", {"form": form, "employee": employee})


@login_required
def deactivate_user(request, pk):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    employee = get_object_or_404(User, pk=pk)
    if employee.pk == request.user.pk:
        messages.error(request, "You can't deactivate your own account.")
        return redirect("user_list")

    if request.method == "POST":
        employee.is_active = False
        employee.save(update_fields=["is_active"])
        messages.success(
            request,
            f"{employee.get_full_name() or employee.username} deactivated. They can no longer log in.",
        )

    return redirect("user_list")


@login_required
def reactivate_user(request, pk):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    employee = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        employee.is_active = True
        employee.save(update_fields=["is_active"])
        messages.success(request, f"{employee.get_full_name() or employee.username} reactivated.")

    return redirect("user_list")


@login_required
@never_cache
def delete_user(request, pk):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    employee = get_object_or_404(User, pk=pk)
    if employee.pk == request.user.pk:
        messages.error(request, "You can't delete your own account.")
        return redirect("user_list")

    if employee.is_active:
        messages.error(request, "Deactivate this account before deleting it.")
        return redirect("user_list")

    record_counts = {
        "tour plan": TourPlan.objects.filter(created_by=employee).count(),
        "doctor assignment": DoctorEmployeeRelation.objects.filter(employee=employee).count(),
        "daily coverage visit": DailyCoverage.objects.filter(created_by=employee).count(),
        "chemist coverage visit": ChemistCoverage.objects.filter(created_by=employee).count(),
        "stockist coverage visit": StockistCoverage.objects.filter(created_by=employee).count(),
    }
    record_counts = {label: n for label, n in record_counts.items() if n}

    if request.method == "POST":
        name = employee.get_full_name() or employee.username
        employee.delete()
        messages.success(request, f"{name} permanently deleted.")
        return redirect("user_list")

    return render(
        request,
        "users/delete_user.html",
        {
            "employee": employee,
            "record_counts": record_counts,
            "total_records": sum(record_counts.values()),
        },
    )


# Positions that sit outside the sales reporting tree — HR/Admin are staff
# roles (HR already sees every report), so they are neither assigned a manager
# nor offered as one.
NON_TEAM_TYPES = {User.UserType.HR, User.UserType.ADMIN}


def _team_users():
    """All sales-line users (excludes HR/Admin/superusers), top position first."""
    users = [
        u for u in User.objects.select_related("manager").all()
        if not u.is_superuser and u.type not in NON_TEAM_TYPES
    ]
    users.sort(key=lambda u: (
        -u.hierarchy_level, u.first_name.lower(), u.last_name.lower(), u.username.lower()
    ))
    return users


@login_required
@never_cache
def team_management(request):
    if not _can_manage_users(request.user):
        raise PermissionDenied

    users = _team_users()
    by_id = {u.pk: u for u in users}

    if request.method == "POST":
        changed = skipped = 0
        for emp in users:
            raw = (request.POST.get(f"manager_{emp.pk}") or "").strip()
            new_manager_id = int(raw) if raw.isdigit() else None
            if new_manager_id == emp.manager_id:
                continue
            if new_manager_id is not None:
                manager = by_id.get(new_manager_id)
                if (
                    manager is None
                    or manager.pk == emp.pk
                    or manager.hierarchy_level <= emp.hierarchy_level
                ):
                    skipped += 1
                    continue
            emp.manager_id = new_manager_id
            emp.save(update_fields=["manager"])
            changed += 1

        if changed:
            messages.success(request, f"Updated team assignment for {changed} employee{'' if changed == 1 else 's'}.")
        if skipped:
            messages.error(request, f"{skipped} change{'' if skipped == 1 else 's'} skipped — a manager must hold a higher position than the employee.")
        if not changed and not skipped:
            messages.info(request, "No changes to save.")
        return redirect("team_management")

    # Per-employee row + the managers they may report to (higher position, active).
    active_users = [u for u in users if u.is_active]
    rows = [
        {
            "employee": emp,
            "options": [m for m in active_users if m.hierarchy_level > emp.hierarchy_level],
        }
        for emp in users
    ]

    # Teams overview — each manager with at least one direct report.
    reports_by_manager = defaultdict(list)
    for u in users:
        if u.manager_id:
            reports_by_manager[u.manager_id].append(u)
    for members in reports_by_manager.values():
        members.sort(key=lambda u: (u.first_name.lower(), u.last_name.lower(), u.username.lower()))
    teams = [
        {"manager": mgr, "members": reports_by_manager[mgr.pk]}
        for mgr in users if mgr.pk in reports_by_manager
    ]
    # Truly floating employees: no manager and not a manager themselves — only
    # HR/superusers can see their reports until they're placed on a team.
    unassigned = [u for u in users if not u.manager_id and u.pk not in reports_by_manager]

    return render(request, "users/team_management.html", {
        "rows": rows,
        "teams": teams,
        "unassigned": unassigned,
    })


def _month_visit_count(user, year, month):
    return DailyCoverage.objects.filter(
        created_by=user, report_date__year=year, report_date__month=month
    ).count()


@login_required
@never_cache
def dashboard(request):
    user = request.user
    today = timezone.localdate()

    hour = timezone.localtime().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    # Today's tour plan (approved one wins if several exist for the date)
    today_plans = list(
        TourPlan.objects.filter(created_by=user, plan_date=today)
        .select_related("area", "worked_with")
    )
    today_plan = next(
        (p for p in today_plans if p.status == TourPlan.Status.APPROVED),
        today_plans[0] if today_plans else None,
    )
    today_approved = bool(today_plan and today_plan.status == TourPlan.Status.APPROVED)

    # Visits this month vs. last month
    visits_month = _month_visit_count(user, today.year, today.month)
    prev_month_end = today.replace(day=1) - timedelta(days=1)
    prev_visits = _month_visit_count(user, prev_month_end.year, prev_month_end.month)
    prev_month_name = calendar.month_name[prev_month_end.month]
    if prev_visits:
        delta = round((visits_month - prev_visits) * 100 / prev_visits)
        visits_trend = "up" if delta > 0 else ("down" if delta < 0 else "flat")
        visits_delta = abs(delta)
    else:
        visits_trend = visits_delta = None

    # Per-category coverage of approved assignments this month.
    # "Covered" = visited at least once; attainment caps each doctor at their
    # class visit target (Super Core 4 / Core 2 / VIP 1).
    relations = list(
        DoctorEmployeeRelation.objects.filter(
            employee=user, status=DoctorEmployeeRelation.Status.APPROVED
        ).values("doctor_id", "msl_number")
    )
    visit_counts = {
        row["doctor"]: row["n"]
        for row in DailyCoverage.objects.filter(
            created_by=user, report_date__year=today.year, report_date__month=today.month
        ).values("doctor").annotate(n=Count("id"))
    }
    msl_by_doctor = {}
    totals = {"super_core": 0, "core": 0, "vip": 0}
    covered = {"super_core": 0, "core": 0, "vip": 0}
    target_total = target_met = 0
    for rel in relations:
        category = _doctor_category(rel["msl_number"])
        msl_by_doctor[rel["doctor_id"]] = rel["msl_number"]
        totals[category] += 1
        visits = visit_counts.get(rel["doctor_id"], 0)
        if visits:
            covered[category] += 1
        target = VISIT_TARGETS[category]
        target_total += target
        target_met += min(visits, target)

    if target_total:
        attainment = round(target_met * 100 / target_total)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        on_track = attainment >= round(today.day * 100 / days_in_month)
    else:
        attainment = None
        on_track = False

    target_rows = [
        {"label": CATEGORY_LABELS[c], "badge": badge, "covered": covered[c], "total": totals[c]}
        for c, badge in (
            ("super_core", "badge--primary"),
            ("core", "badge--neutral"),
            ("vip", "badge--neutral"),
        )
    ]

    pending_approvals = (
        TourPlan.objects.filter(created_by=user, status=TourPlan.Status.PENDING).count()
        + DoctorEmployeeRelation.objects.filter(
            employee=user, status=DoctorEmployeeRelation.Status.PENDING
        ).count()
    )

    todays_coverage = list(
        DailyCoverage.objects.filter(created_by=user, report_date=today)
        .select_related("doctor")
        .order_by("call_time")
    )
    for cov in todays_coverage:
        cov.category_label = CATEGORY_LABELS[_doctor_category(msl_by_doctor.get(cov.doctor_id))]

    upcoming_plans = list(
        TourPlan.objects.filter(
            created_by=user,
            plan_date__gt=today,
            plan_date__lte=today + timedelta(days=7),
        )
        .select_related("area")
        .order_by("plan_date")
    )

    return render(request, "dashboard.html", {
        "greeting": greeting,
        "today": today,
        "today_plan": today_plan,
        "today_approved": today_approved,
        "visits_month": visits_month,
        "visits_trend": visits_trend,
        "visits_delta": visits_delta,
        "prev_month_name": prev_month_name,
        "sc_covered": covered["super_core"],
        "sc_total": totals["super_core"],
        "sc_remaining": totals["super_core"] - covered["super_core"],
        "has_assignments": bool(relations),
        "attainment": attainment,
        "on_track": on_track,
        "target_rows": target_rows,
        "pending_approvals": pending_approvals,
        "todays_coverage": todays_coverage,
        "upcoming_plans": upcoming_plans,
    })
