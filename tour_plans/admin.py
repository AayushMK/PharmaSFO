from django.contrib import admin

from .models import Area, TourPlan


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(TourPlan)
class TourPlanAdmin(admin.ModelAdmin):
    list_display = ("plan_date", "area", "worked_with", "reporting_date", "created_by", "status")
    search_fields = ("area__name", "remarks", "worked_with__username", "created_by__username")
    list_filter = ("plan_date", "reporting_date", "status")
