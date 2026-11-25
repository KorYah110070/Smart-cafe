import calendar
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView

from accounts.mixins import StaffRequiredMixin
from tables.models import FloorLandmark, Table

from .forms import ReservationEditForm
from .models import Reservation
from .services import (
    ReservationError,
    cancel_reservation,
    confirm_reservation,
    edit_reservation,
    seat_walkin,
    table_availability_for_date,
)

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


class MyReservationListView(LoginRequiredMixin, ListView):
    """FR-14, FR-22: ลูกค้า/พนักงานดูรายการการจอง"""

    model = Reservation
    template_name = "reservations/my_reservations.html"
    context_object_name = "reservations"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member or user.is_admin_role or user.is_superuser:
            return Reservation.objects.all().prefetch_related("tables")
        return Reservation.objects.filter(customer=user).prefetch_related("tables")


class ReservationDateStepView(LoginRequiredMixin, View):
    """
    Step 1: ลูกค้าเลือก "วันที่" ต้องการจองก่อน จากปฏิทินรายเดือน (FR-06)
    จองได้เฉพาะวันนี้ถึงวันสุดท้ายของเดือนปัจจุบันเท่านั้น (business rule เดิม)
    """

    template_name = "reservations/create_step1_date.html"

    def get(self, request):
        today = timezone.localdate()
        last_day = calendar.monthrange(today.year, today.month)[1]
        last_date = today.replace(day=last_day)

        cal = calendar.Calendar(firstweekday=6)  # เริ่มสัปดาห์ที่วันอาทิตย์
        weeks = []
        for week in cal.monthdatescalendar(today.year, today.month):
            week_cells = []
            for day in week:
                in_month = day.month == today.month
                bookable = in_month and today <= day <= last_date
                week_cells.append(
                    {
                        "day": day,
                        "in_month": in_month,
                        "is_today": day == today,
                        "bookable": bookable,
                    }
                )
            weeks.append(week_cells)

        context = {
            "weeks": weeks,
            "month_label": f"{THAI_MONTHS[today.month]} {today.year + 543}",
            "weekday_labels": ["อา", "จ", "อ", "พ", "พฤ", "ศ", "ส"],
        }
        return render(request, self.template_name, context)


class ReservationFloorPlanBookingView(LoginRequiredMixin, View):
    """
    Step 2: หลังเลือกวันที่แล้ว -> เห็นผังร้านของวันนั้น
    โต๊ะที่มีคนจองไปแล้ว/ปิดใช้งานจะกดไม่ได้ (เทาและคลิกไม่ได้)
    โต๊ะว่างกดเลือกได้ (เลือกได้หลายตัวถ้าจำนวนคนเกินโต๊ะเดียว - รองรับโต๊ะรวม)
    """

    template_name = "reservations/create_step2_floorplan.html"

    def _parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def _validate_window(self, reservation_date):
        today = timezone.localdate()
        if reservation_date is None:
            return "วันที่ไม่ถูกต้อง กรุณาเลือกวันที่อีกครั้ง"
        if reservation_date < today:
            return "ไม่สามารถจองวันที่ผ่านมาแล้วได้"
        if reservation_date.month != today.month or reservation_date.year != today.year:
            return "สามารถจองได้เฉพาะวันที่อยู่ภายในเดือนปัจจุบันเท่านั้น"
        return None

    def get(self, request, date_str):
        reservation_date = self._parse_date(date_str)
        error = self._validate_window(reservation_date)
        if error:
            messages.error(request, error)
            return redirect("reservations:create")

        busy_ids = table_availability_for_date(reservation_date)
        tables = Table.objects.order_by("zone", "table_number")
        landmarks = FloorLandmark.objects.all()

        context = {
            "reservation_date": reservation_date,
            "reservation_date_display": f"{reservation_date.day} {THAI_MONTHS[reservation_date.month]} {reservation_date.year + 543}",
            "tables": tables,
            "landmarks": landmarks,
            "busy_ids": busy_ids,
        }
        return render(request, self.template_name, context)

    def post(self, request, date_str):
        reservation_date = self._parse_date(date_str)
        error = self._validate_window(reservation_date)
        if error:
            messages.error(request, error)
            return redirect("reservations:create")

        table_ids = request.POST.getlist("table_ids")
        tables = list(Table.objects.filter(id__in=table_ids))

        try:
            party_size = int(request.POST.get("party_size") or 0)
        except ValueError:
            party_size = 0

        if party_size < 1:
            messages.error(request, "กรุณาระบุจำนวนคน")
            return redirect("reservations:create_floorplan", date_str=date_str)

        try:
            reservation = confirm_reservation(
                user=request.user,
                reservation_date=reservation_date,
                party_size=party_size,
                tables=tables,
            )
        except ReservationError as exc:
            messages.error(request, str(exc))
            return redirect("reservations:create_floorplan", date_str=date_str)

        reservation.extra_chair_requested = "extra_chair_requested" in request.POST
        reservation.save(update_fields=["extra_chair_requested"])

        messages.success(request, "จองโต๊ะสำเร็จ! ระบบได้บันทึกการจองของคุณเรียบร้อยแล้ว")
        return redirect("reservations:my_reservations")


class EditReservationView(LoginRequiredMixin, View):
    """FR-32, FR-33: แก้ไขการจองที่มีอยู่แล้ว (วันที่/จำนวนคน - ระบบหาโต๊ะใหม่ให้อัตโนมัติถ้าจำเป็น)"""

    template_name = "reservations/edit_reservation.html"

    def get(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk, customer=request.user)
        initial = {
            "reservation_date": reservation.reservation_date,
            "party_size": reservation.party_size,
        }
        form = ReservationEditForm(initial=initial)
        return render(
            request, self.template_name, {"form": form, "reservation": reservation}
        )

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk, customer=request.user)
        form = ReservationEditForm(request.POST)
        if not form.is_valid():
            return render(
                request, self.template_name, {"form": form, "reservation": reservation}
            )

        try:
            edit_reservation(
                reservation,
                new_date=form.cleaned_data["reservation_date"],
                new_party_size=form.cleaned_data["party_size"],
            )
        except ReservationError as exc:
            messages.error(request, str(exc))
            return render(
                request, self.template_name, {"form": form, "reservation": reservation}
            )

        messages.success(request, "แก้ไขการจองเรียบร้อยแล้ว")
        return redirect("reservations:my_reservations")


class CancelReservationView(LoginRequiredMixin, View):
    """FR-07: ยกเลิกการจอง"""

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk, customer=request.user)
        try:
            cancel_reservation(reservation)
            messages.success(request, "ยกเลิกการจองเรียบร้อยแล้ว")
        except ReservationError as exc:
            messages.error(request, str(exc))
        return redirect("reservations:my_reservations")


class AdminReservationListView(StaffRequiredMixin, ListView):
    """
    FR-22: หน้า 'จัดการการจอง' ของแอดมิน/พนักงาน - ดูการจองทั้งหมด กรองตามวันที่/สถานะ
    และเปลี่ยนสถานะการจองได้โดยตรง (reserved -> preparing -> served / cancelled)
    """

    model = Reservation
    template_name = "reservations/admin_list.html"
    context_object_name = "reservations"
    paginate_by = 30

    def get_queryset(self):
        qs = Reservation.objects.all().select_related("customer").prefetch_related("tables")
        date_filter = self.request.GET.get("date")
        status_filter = self.request.GET.get("status")
        if date_filter:
            qs = qs.filter(reservation_date=date_filter)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Reservation.Status.choices
        context["selected_date"] = self.request.GET.get("date", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["today"] = timezone.localdate().isoformat()
        return context


class AdminReservationStatusUpdateView(StaffRequiredMixin, View):
    """เปลี่ยนสถานะการจองจากหน้า 'จัดการการจอง' (ปุ่มในแต่ละแถว)"""

    def post(self, request, pk):
        reservation = get_object_or_404(Reservation, pk=pk)
        new_status = request.POST.get("status")

        if new_status == Reservation.Status.CANCELLED:
            try:
                cancel_reservation(reservation)
                messages.success(request, f"ยกเลิกการจอง #{reservation.id} เรียบร้อยแล้ว")
            except ReservationError as exc:
                messages.error(request, str(exc))
        elif new_status in dict(Reservation.Status.choices):
            reservation.status = new_status
            reservation.save(update_fields=["status", "updated_at"])
            messages.success(request, f"อัปเดตสถานะการจอง #{reservation.id} เรียบร้อยแล้ว")
        else:
            messages.error(request, "สถานะไม่ถูกต้อง")

        redirect_url = reverse("reservations:admin_list")
        query = request.POST.get("next_query", "")
        if query:
            redirect_url += f"?{query}"
        return redirect(redirect_url)


class WalkinSeatView(StaffRequiredMixin, View):
    """
    พนักงาน/แอดมิน 'รับลูกค้าวอล์กอิน': เลือกโต๊ะที่ว่าง ใส่ชื่อลูกค้า + จำนวนคน
    ระบบจะสร้างการจองของวันนี้ให้ทันที แล้วพาไปหน้าสั่งเมนูสำหรับโต๊ะนั้นต่อเลย
    """

    template_name = "reservations/walkin_form.html"

    def get(self, request):
        today = timezone.localdate()
        busy_ids = table_availability_for_date(today)
        available_tables = Table.objects.exclude(id__in=busy_ids).order_by("zone", "table_number")
        return render(request, self.template_name, {"available_tables": available_tables})

    def post(self, request):
        table_id = request.POST.get("table_id")
        guest_name = request.POST.get("guest_name", "")
        try:
            party_size = int(request.POST.get("party_size") or 0)
        except ValueError:
            party_size = 0

        table = Table.objects.filter(id=table_id).first()
        if table is None:
            messages.error(request, "กรุณาเลือกโต๊ะ")
            return redirect("reservations:walkin_seat")

        try:
            reservation = seat_walkin(table=table, guest_name=guest_name, party_size=party_size)
        except ReservationError as exc:
            messages.error(request, str(exc))
            return redirect("reservations:walkin_seat")

        messages.success(
            request, f"รับลูกค้าวอล์กอิน '{reservation.guest_name}' เข้าโต๊ะ {table.table_number} เรียบร้อยแล้ว"
        )
        return redirect("orders:staff_create", reservation_id=reservation.id)
