from calendar import month_name
from datetime import date

import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache

from users.models import User

from .forms import TourPlanBulkForm
from .models import Area, TourPlan


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
