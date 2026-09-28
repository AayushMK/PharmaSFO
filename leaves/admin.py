from django.contrib import admin

from .models import LeaveRequest


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ("created_by", "leave_type", "start_date", "end_date", "status", "reviewed_by")
    list_filter = ("status", "leave_type")
    search_fields = ("created_by__username", "created_by__first_name", "reason")
