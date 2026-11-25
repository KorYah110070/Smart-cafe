from django.contrib import admin

from .models import Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("title", "discount_percent", "start_date", "end_date", "is_active")
    list_filter = ("is_active",)
