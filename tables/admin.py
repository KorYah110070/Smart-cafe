from django.contrib import admin

from .models import FloorLandmark, Table, TableGroup, TableGroupMember


class TableGroupMemberInline(admin.TabularInline):
    model = TableGroupMember
    extra = 1


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("table_number", "zone", "capacity", "shape", "status")
    list_filter = ("zone", "shape", "status")
    list_editable = ("status",)
    search_fields = ("table_number", "zone")


@admin.register(FloorLandmark)
class FloorLandmarkAdmin(admin.ModelAdmin):
    list_display = ("display_label", "kind", "pos_x", "pos_y", "width_px", "height_px")
    list_filter = ("kind",)


@admin.register(TableGroup)
class TableGroupAdmin(admin.ModelAdmin):
    list_display = ("group_name", "total_capacity_display")
    inlines = [TableGroupMemberInline]

    def total_capacity_display(self, obj):
        return obj.total_capacity()

    total_capacity_display.short_description = "ความจุรวม"
