import csv
from datetime import datetime, timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from accounts.mixins import StaffRequiredMixin
from accounts.models import User
from menus.models import MenuItem
from orders.models import Order, OrderItem
from promotions.models import Promotion
from reservations.models import Reservation
from tables.models import FloorLandmark, Table

from .forms import AdminPasswordChangeForm, AdminProfileForm, SiteSettingsForm
from .models import SiteSettings

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def _parse_date(value, fallback):
    if not value:
        return fallback
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return fallback


class DashboardView(StaffRequiredMixin, TemplateView):
    """
    FR-23, FR-24: หน้าแรกของระบบจัดการฝั่งแอดมิน/พนักงาน (Admin Dashboard)
    แสดงผังโต๊ะของวันที่เลือก (เลื่อนดูวันอื่นได้), รายการจองของวันนั้น, การจองล่วงหน้า 7 วันข้างหน้า
    และสรุปสถานะโต๊ะ/ข้อมูลการจองโดยรวม

    หมายเหตุสถาปัตยกรรม: Table.status เป็นฟิลด์ 'สถานะปัจจุบัน' แบบ global ไม่ผูกกับวันที่
    (ตามที่ออกแบบไว้ตั้งแต่ต้นของระบบ) ดังนั้นเมื่อแอดมินเลือกดู 'วันนี้' ผังจะแสดงสถานะโต๊ะแบบเรียลไทม์
    (available/reserved/preparing/served) ตรง ๆ จาก Table.status
    แต่เมื่อเลือกดูวันอื่น (อดีต/อนาคต) ระบบจะคำนวณสถานะโต๊ะแบบย้อนหลัง/ล่วงหน้าจากตาราง Reservation
    แทน (มีจองในวันนั้น = reserved, ไม่มี = available) เพราะสถานะ preparing/served มีความหมายเฉพาะ
    'ตอนนี้' เท่านั้น
    """

    template_name = "dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        selected_date = _parse_date(self.request.GET.get("date"), today)
        is_today = selected_date == today

        tables = Table.objects.order_by("zone", "table_number")

        reservations_for_day = (
            Reservation.objects.filter(reservation_date=selected_date)
            .exclude(status=Reservation.Status.CANCELLED)
            .select_related("customer")
            .prefetch_related("tables")
            .order_by("customer__username")
        )

        # แผนที่ table_id -> reservation ของวันนั้น (ถ้ามี) ใช้ตอนคำนวณสถานะย้อนหลัง/ล่วงหน้า
        table_id_to_reservation = {}
        for r in reservations_for_day:
            for t in r.tables.all():
                table_id_to_reservation[t.id] = r

        table_rows = []
        status_counts = {"available": 0, "reserved": 0, "preparing": 0, "served": 0}
        for t in tables:
            if is_today:
                effective_status = t.status
            else:
                r = table_id_to_reservation.get(t.id)
                effective_status = "reserved" if r else "available"
            status_counts[effective_status] = status_counts.get(effective_status, 0) + 1
            table_rows.append(
                {
                    "table": t,
                    "status": effective_status,
                    "status_display": dict(Table.Status.choices).get(effective_status, effective_status),
                }
            )

        upcoming_start = today + timedelta(days=1)
        upcoming_end = today + timedelta(days=7)
        upcoming_reservations = (
            Reservation.objects.filter(
                reservation_date__gte=upcoming_start, reservation_date__lte=upcoming_end
            )
            .exclude(status=Reservation.Status.CANCELLED)
            .select_related("customer")
            .prefetch_related("tables")
            .order_by("reservation_date", "customer__username")[:20]
        )

        context.update(
            {
                "table_rows": table_rows,
                "landmarks": FloorLandmark.objects.all(),
                "selected_date": selected_date,
                "selected_date_iso": selected_date.isoformat(),
                "selected_date_thai": f"{selected_date.day} {THAI_MONTHS[selected_date.month]} {selected_date.year + 543}",
                "is_today": is_today,
                "today_iso": today.isoformat(),
                "prev_date_iso": (selected_date - timedelta(days=1)).isoformat(),
                "next_date_iso": (selected_date + timedelta(days=1)).isoformat(),
                "reservations_for_day": reservations_for_day,
                "upcoming_reservations": upcoming_reservations,
                "total_tables": tables.count(),
                "available_count": status_counts.get("available", 0),
                "reserved_count": status_counts.get("reserved", 0),
                "preparing_count": status_counts.get("preparing", 0),
                "served_count": status_counts.get("served", 0),
                "reservation_count_for_day": reservations_for_day.count(),
                "customer_count_for_day": reservations_for_day.values("customer_id").distinct().count(),
            }
        )
        return context


class CustomerStatsView(StaffRequiredMixin, TemplateView):
    """หน้า 'สถิติลูกค้า' - ภาพรวมจำนวนลูกค้า, ลูกค้าใหม่, ลูกค้าประจำ (จองบ่อยที่สุด)"""

    template_name = "dashboard/customer_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        month_start = today.replace(day=1)

        customers = User.objects.filter(role=User.Role.CUSTOMER)
        context["total_customers"] = customers.count()
        context["new_customers_this_month"] = customers.filter(date_joined__date__gte=month_start).count()

        top_customers = (
            customers.annotate(reservation_count=Count("reservations"))
            .filter(reservation_count__gt=0)
            .order_by("-reservation_count")[:10]
        )
        context["top_customers"] = top_customers

        context["total_reservations"] = Reservation.objects.exclude(
            status=Reservation.Status.CANCELLED
        ).count()
        context["active_promotions"] = Promotion.objects.filter(is_active=True).count()
        context["available_menu_items"] = MenuItem.objects.filter(is_available=True).count()
        return context


def _period_range(period, today):
    """คืนค่า (start, end, prev_start, prev_end, period_label) ตามช่วงเวลาที่เลือก (รายวัน/รายเดือน)"""
    if period == "monthly":
        start = today.replace(day=1)
        end = today
        prev_month_end = start - timedelta(days=1)
        prev_start = prev_month_end.replace(day=1)
        prev_end = prev_month_end
        label = f"{THAI_MONTHS[today.month]} {today.year + 543}"
    else:
        start = today
        end = today
        prev_start = today - timedelta(days=1)
        prev_end = prev_start
        label = f"วันที่ {today.day} {THAI_MONTHS[today.month]} {today.year + 543}"
    return start, end, prev_start, prev_end, label


def _orders_total(orders_qs):
    """รวมยอดขายของ queryset ออเดอร์ (คำนวณจาก OrderItem ของแต่ละออเดอร์)"""
    total = Decimal("0")
    for order in orders_qs:
        total += order.total_price()
    return total


class SalesStatsView(StaffRequiredMixin, TemplateView):
    """
    หน้า 'สถิติยอดขาย' ของแอดมิน/พนักงาน
    ดูยอดขายรายวัน/รายเดือน, จำนวนออเดอร์, ยอดขายเฉลี่ยต่อออเดอร์, เมนูขายดีที่สุด,
    เปรียบเทียบยอดขายกับช่วงก่อนหน้า (เมื่อวาน/เดือนก่อน) และดาวน์โหลดรายงาน CSV
    หมายเหตุ: ระบบยังไม่มีสถานะ 'ชำระเงินแล้ว' แยกต่างหาก จึงนับทุกออเดอร์ที่สร้างขึ้นในช่วงเวลานั้นเป็นยอดขาย
    """

    template_name = "dashboard/sales_stats.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localdate()
        period = self.request.GET.get("period", "daily")
        if period not in ("daily", "monthly"):
            period = "daily"

        start, end, prev_start, prev_end, period_label = _period_range(period, today)

        orders_qs = (
            Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
            .select_related("customer")
            .prefetch_related("items__menu_item")
        )
        prev_orders_qs = Order.objects.filter(
            created_at__date__gte=prev_start, created_at__date__lte=prev_end
        ).prefetch_related("items")

        total_sales = _orders_total(orders_qs)
        order_count = orders_qs.count()
        avg_per_order = (total_sales / order_count) if order_count else Decimal("0")

        prev_total_sales = _orders_total(prev_orders_qs)
        if prev_total_sales > 0:
            change_pct = ((total_sales - prev_total_sales) / prev_total_sales) * 100
        else:
            change_pct = None

        # หมายเหตุ: คำนวณยอดขายต่อเมนู (revenue) แบบ python-side เพื่อหลีกเลี่ยงความยุ่งยากของ
        # ExpressionWrapper(F(...) * F(...)) และให้โค้ดอ่านง่ายสำหรับโปรเจคขนาดนี้
        best_seller_rows = []
        for row in (
            OrderItem.objects.filter(order__in=orders_qs)
            .values("menu_item__name")
            .annotate(qty=Sum("quantity"))
            .order_by("-qty")[:5]
        ):
            revenue = sum(
                oi.subtotal()
                for oi in OrderItem.objects.filter(
                    order__in=orders_qs, menu_item__name=row["menu_item__name"]
                )
            )
            best_seller_rows.append(
                {"name": row["menu_item__name"], "qty": row["qty"], "revenue": revenue}
            )

        context.update(
            {
                "period": period,
                "period_label": period_label,
                "total_sales": total_sales,
                "order_count": order_count,
                "avg_per_order": avg_per_order,
                "prev_total_sales": prev_total_sales,
                "change_pct": change_pct,
                "best_sellers": best_seller_rows,
                "orders": orders_qs.order_by("-created_at")[:50],
            }
        )
        return context


class SalesReportDownloadView(StaffRequiredMixin, View):
    """ดาวน์โหลดรายงานยอดขาย (CSV) ตามช่วงเวลาที่เลือกในหน้า 'สถิติยอดขาย'"""

    def get(self, request):
        today = timezone.localdate()
        period = request.GET.get("period", "daily")
        if period not in ("daily", "monthly"):
            period = "daily"
        start, end, _, _, _ = _period_range(period, today)

        orders = (
            Order.objects.filter(created_at__date__gte=start, created_at__date__lte=end)
            .select_related("customer")
            .prefetch_related("items")
            .order_by("created_at")
        )

        response = HttpResponse(content_type="text/csv")
        filename = f"sales_report_{period}_{today.isoformat()}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        writer = csv.writer(response)
        writer.writerow(
            ["Order ID", "วันที่/เวลา", "ประเภท", "ลูกค้า", "สถานะ", "จำนวนรายการ", "ชำระเงิน", "วิธีชำระเงิน", "ยอดรวม (บาท)"]
        )
        for order in orders:
            writer.writerow(
                [
                    order.id,
                    timezone.localtime(order.created_at).strftime("%d/%m/%Y %H:%M"),
                    order.get_order_type_display(),
                    order.customer_display_name,
                    order.get_status_display(),
                    order.items.count(),
                    "จ่ายแล้ว" if order.is_paid else "ยังไม่จ่าย",
                    order.get_payment_method_display() if order.payment_method else "-",
                    order.total_price(),
                ]
            )
        writer.writerow([])
        writer.writerow(["รวมยอดขายทั้งหมด", "", "", "", "", "", "", "", _orders_total(orders)])
        return response


class SiteSettingsView(StaffRequiredMixin, View):
    """
    หน้า 'ตั้งค่าระบบ' ของแอดมิน/พนักงาน - ข้อมูลร้าน (ชื่อ/ที่อยู่/เบอร์โทร/เวลาเปิด-ปิด/โลโก้)
    และข้อมูลผู้ดูแลระบบของบัญชีที่ล็อกอินอยู่ (ชื่อผู้ใช้/อีเมล/เบอร์โทร + เปลี่ยนรหัสผ่าน)
    ใช้ hidden field "form_name" เพื่อแยกว่าฟอร์มไหนถูก submit มา (มี 3 ฟอร์มในหน้าเดียว)
    """

    template_name = "dashboard/settings.html"

    def get(self, request):
        site_settings = SiteSettings.load()
        context = {
            "settings_form": SiteSettingsForm(instance=site_settings),
            "profile_form": AdminProfileForm(instance=request.user),
            "password_form": AdminPasswordChangeForm(user=request.user),
            "site_settings": site_settings,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        site_settings = SiteSettings.load()
        form_name = request.POST.get("form_name")

        settings_form = SiteSettingsForm(instance=site_settings)
        profile_form = AdminProfileForm(instance=request.user)
        password_form = AdminPasswordChangeForm(user=request.user)

        if form_name == "site_settings":
            settings_form = SiteSettingsForm(request.POST, request.FILES, instance=site_settings)
            if settings_form.is_valid():
                settings_form.save()
                messages.success(request, "บันทึกข้อมูลร้านเรียบร้อยแล้ว")
                return redirect("dashboard:settings")
        elif form_name == "profile":
            profile_form = AdminProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "บันทึกข้อมูลผู้ดูแลระบบเรียบร้อยแล้ว")
                return redirect("dashboard:settings")
        elif form_name == "password":
            password_form = AdminPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "เปลี่ยนรหัสผ่านเรียบร้อยแล้ว")
                return redirect("dashboard:settings")

        context = {
            "settings_form": settings_form,
            "profile_form": profile_form,
            "password_form": password_form,
            "site_settings": site_settings,
        }
        return render(request, self.template_name, context)
