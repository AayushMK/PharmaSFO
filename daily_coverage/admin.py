from django.contrib import admin

from .models import Chemist, DailyCoverage, Stockist


@admin.register(DailyCoverage)
class DailyCoverageAdmin(admin.ModelAdmin):
    list_display = ("report_date", "doctor", "actual_working_place", "call_time", "created_by")
    search_fields = ("doctor__name", "products", "worked_with", "remarks")
    list_filter = ("report_date",)


@admin.register(Chemist)
class ChemistAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "phone")
    search_fields = ("name", "area__name", "phone")
    list_filter = ("area",)


@admin.register(Stockist)
class StockistAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "phone")
    search_fields = ("name", "area__name", "phone")
    list_filter = ("area",)
