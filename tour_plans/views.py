from calendar import month_name
from datetime import date

import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache

from users.models import User

from .forms import TourPlanBulkForm
from .models import Area, TourPlan


def _is_hr_user(user):
    return user.is_authenticated and user.is_staff and user.type == "HR"


@login_required
@never_cache
def tour_plan_list(request):
    selected_month = request.GET.get("month")
    current_year = date.today().year
    month_choices = [
        (f"{year}-{month:02d}", f"{month_name[month]} {year}")
        for year in [current_year, current_year + 1]
        for month in range(1, 13)
    ]

    if not selected_month:
        selected_month = f"{current_year}-{date.today().month:02d}"

    tour_plans = TourPlan.objects.filter(plan_date__year=selected_month[:4], plan_date__month=selected_month[5:7])
    if request.user.is_authenticated:
        tour_plans = tour_plans.filter(created_by=request.user)

    selected_month_label = next(
        (label for value, label in month_choices if value == selected_month),
        selected_month,
    )

    return render(
        request,
        "tour_plans/tour_plan_list.html",
        {
            "tour_plans": tour_plans.order_by("plan_date"),
            "selected_month": selected_month,
            "selected_month_label": selected_month_label,
            "month_choices": month_choices,
        },
    )


@login_required
@never_cache
def add_tour_plan(request):
    if request.method == "POST":
        form = TourPlanBulkForm(request.POST)
        if form.is_valid():
            entries = form.cleaned_data.get("entries") or []
            created = 0
            for entry in entries:
                plan_date = entry.get("plan_date")
                area_id = entry.get("area")
                worked_with_id = entry.get("worked_with") or None
                remarks = entry.get("remarks") or ""
                if not plan_date or not area_id:
                    continue
                TourPlan.objects.create(
                    created_by=request.user,
                    plan_date=plan_date,
                    area_id=area_id,
                    worked_with_id=worked_with_id,
                    remarks=remarks,
                )
                created += 1
            skipped = len(entries) - created
            if created:
                messages.success(request, f"{created} day{'s' if created != 1 else ''} submitted for HR approval.")
            if skipped:
                messages.warning(request, f"{skipped} entr{'ies' if skipped != 1 else 'y'} skipped because the date or area was missing.")
            if not entries:
                messages.error(request, "No days were submitted. Add at least one day.")
            return redirect("tour_plans")
    else:
        form = TourPlanBulkForm()

    area_options = [
        {"value": str(area.pk), "label": area.name} for area in Area.objects.order_by("name")
    ]
    user_options = [
        {"value": str(user.pk), "label": user.get_full_name() or user.username}
        for user in User.objects.order_by("username")
    ]

    return render(
        request,
        "tour_plans/add_tour_plan.html",
        {
            "form": form,
            "area_options": json.dumps(area_options),
            "user_options": json.dumps(user_options),
        },
    )


@login_required
@never_cache
def hr_review_tour_plans(request):
    if not _is_hr_user(request.user):
        raise PermissionDenied

    pending_plans = (
        TourPlan.objects.filter(status=TourPlan.Status.PENDING)
        .select_related("created_by")
        .order_by("created_by__username", "plan_date")
    )

    employees_with_pending = []
    seen = set()
    for plan in pending_plans:
        emp = plan.created_by
        if emp and emp.pk not in seen:
            seen.add(emp.pk)
            employees_with_pending.append({
                "employee": emp,
                "count": pending_plans.filter(created_by=emp).count(),
            })

    return render(
        request,
        "tour_plans/hr_review_tour_plans.html",
        {"employees_with_pending": employees_with_pending},
    )


@login_required
@never_cache
def hr_review_employee_tour_plans(request, employee_id):
    if not _is_hr_user(request.user):
        raise PermissionDenied

    employee = get_object_or_404(get_user_model(), pk=employee_id)
    pending_plans = (
        TourPlan.objects.filter(created_by=employee, status=TourPlan.Status.PENDING)
        .select_related("area", "worked_with")
        .order_by("plan_date")
    )

    if request.method == "POST":
        plan_id = request.POST.get("plan_id")
        action = request.POST.get("action")
        plan = get_object_or_404(TourPlan, pk=plan_id, created_by=employee)

        if action == "approve":
            plan.status = TourPlan.Status.APPROVED
            messages.success(request, f"Approved {plan.plan_date:%-d %b} in {plan.area.name}. Coverage logging is now open.")
        else:
            plan.status = TourPlan.Status.REJECTED
            messages.warning(request, f"Rejected the plan for {plan.plan_date:%-d %b} in {plan.area.name}.")
        plan.save()
        return redirect("hr_review_employee_tour_plans", employee_id=employee.id)

    return render(
        request,
        "tour_plans/hr_review_employee_tour_plans.html",
        {"employee": employee, "pending_plans": pending_plans},
    )
