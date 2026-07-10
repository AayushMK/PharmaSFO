from django.contrib import admin
from .models import Doctor, Hospital


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "phone")
    search_fields = ("name", "area__name", "phone")
    list_filter = ("area",)


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "nmc_number", "hospital", "area", "phone", "email")
    search_fields = ("name", "nmc_number", "area", "phone", "email", "hospital__name")
    list_filter = ("area",)
    list_select_related = ("hospital",)
