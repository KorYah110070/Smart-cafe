from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CafeUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("ข้อมูลร้าน (Smart Cafe)", {"fields": ("role", "phone_number")}),
    )
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
