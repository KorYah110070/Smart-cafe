from django.contrib import admin

from .models import Reservation, ReservationHistory, ReservationTable


class ReservationTableInline(admin.TabularInline):
    model = ReservationTable
    extra = 0


class ReservationHistoryInline(admin.TabularInline):
    model = ReservationHistory
    extra = 0
    readonly_fields = ("field_changed", "old_value", "new_value", "changed_at")
    can_delete = False


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "customer",
        "reservation_date",
        "party_size",
        "table_numbers_display",
        "status",
    )
    list_filter = ("status", "reservation_date")
    search_fields = ("customer__username",)
    inlines = [ReservationTableInline, ReservationHistoryInline]
