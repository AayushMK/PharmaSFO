from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "type", "manager", "email", "is_staff")
    list_filter = ("type", "is_staff", "is_active")
    raw_id_fields = ("manager",)
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Role", {"fields": ("type", "manager")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Role", {"fields": ("type",)}),
    )
