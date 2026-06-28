from django.contrib import admin

from .models import DailyCoverage


@admin.register(DailyCoverage)
class DailyCoverageAdmin(admin.ModelAdmin):
    list_display = ("report_date", "doctor", "actual_working_place", "call_time", "created_by")
    search_fields = ("doctor__name", "products", "worked_with", "remarks")
    list_filter = ("report_date",)
