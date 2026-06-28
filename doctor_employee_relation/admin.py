from django.contrib import admin

from .models import DoctorEmployeeRelation


@admin.register(DoctorEmployeeRelation)
class DoctorEmployeeRelationAdmin(admin.ModelAdmin):
    list_display = ("employee", "doctor", "assigned_at")
    list_filter = ("employee", "doctor")
    search_fields = ("employee__username", "doctor__name")
    ordering = ("employee__username", "doctor__name")
