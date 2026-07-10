import calendar
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from daily_coverage.models import DailyCoverage
from doctor_employee_relation.models import DoctorEmployeeRelation
from reports.views import CATEGORY_LABELS, VISIT_TARGETS, _doctor_category
from tour_plans.models import TourPlan

from .forms import UserCreateForm


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
                f"({new_user.get_type_display()}) added — they can log in now.",
            )
            return redirect("add_user")
    else:
        form = UserCreateForm()

    return render(request, "users/add_user.html", {"form": form})


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
