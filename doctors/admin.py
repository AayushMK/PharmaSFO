from django.contrib import admin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ("name", "nmc_number", "area")
    search_fields = ("name", "nmc_number", "area")
    list_filter = ("area",)
