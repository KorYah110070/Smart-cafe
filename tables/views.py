import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import TableForm, TableGroupForm
from .models import FloorLandmark, Table, TableGroup

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
]


def thai_date_today():
    today = timezone.localdate()
    return f"{today.day} {THAI_MONTHS[today.month]} {today.year + 543}"


class FloorPlanView(ListView):
    """
    หน้าหลักของลูกค้า (Home page): ผังร้านของวันนี้ + ทางลัดไปยัง 4 ฟีเจอร์หลัก
    FR-04, FR-05: ดูผังร้านและตรวจสอบสถานะโต๊ะว่าง (ไม่บังคับล็อกอินสำหรับดูอย่างเดียว)
    Business rule: ลูกค้าเห็นเฉพาะสถานะ 'ว่าง / ไม่ว่าง'
    พนักงานและผู้ดูแลระบบเห็นสถานะโต๊ะทั้งหมด (available/reserved/preparing/served)
    เมนู / โปรโมชั่น / แชทบอท ดูได้เลยแม้ยังไม่ล็อกอิน มีแค่ "จองโต๊ะ" เท่านั้นที่ต้อง
    สมัครสมาชิก/เข้าสู่ระบบก่อน (ควบคุมที่ template ด้วยการเช็ค user.is_authenticated
    เฉพาะปุ่มจองโต๊ะ + ลิงก์ไป login พร้อม ?next=)
    """

    model = Table
    template_name = "tables/floor_plan.html"
    context_object_name = "tables"

    def get_queryset(self):
        return Table.objects.order_by("zone", "table_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["show_detailed_status"] = user.is_authenticated and (
            user.is_staff_member or user.is_admin_role or user.is_superuser
        )
        context["today_thai"] = thai_date_today()

        from ai_assistant.services import personalized_recommendation

        context["ai_recommendation"] = personalized_recommendation(
            user if user.is_authenticated else None
        )

        tables = context["tables"]
        total = tables.count()
        available_count = tables.filter(status=Table.Status.AVAILABLE).count()
        context["total_tables"] = total
        context["available_count"] = available_count
        context["occupied_count"] = total - available_count
        context["landmarks"] = FloorLandmark.objects.all()

        from menus.models import MenuItem
        from promotions.models import Promotion

        today = timezone.localdate()
        context["menu_count"] = MenuItem.objects.filter(is_available=True).count()
        active_promotions = Promotion.objects.filter(
            is_active=True, start_date__lte=today, end_date__gte=today
        ).order_by("-start_date")
        context["promotion_count"] = active_promotions.count()
        context["hero_promotions"] = active_promotions[:5]
        return context


class TableManageListView(StaffRequiredMixin, ListView):
    """
    FR-23: หน้า 'จัดการโต๊ะ' ของแอดมิน/พนักงาน - ดูรายการโต๊ะทั้งหมด พร้อมลิงก์แก้ไข/ลบ
    และลิงก์ไปหน้าจัดการชุดโต๊ะรวม (TableGroup)
    """

    model = Table
    template_name = "tables/manage_list.html"
    context_object_name = "tables"
    queryset = Table.objects.order_by("zone", "table_number")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["groups"] = TableGroup.objects.prefetch_related("tables")
        return context


class TableCreateView(StaffRequiredMixin, CreateView):
    model = Table
    form_class = TableForm
    template_name = "tables/table_form.html"
    success_url = reverse_lazy("tables:manage")

    def get_success_url(self):
        next_url = self.request.POST.get("next")
        if next_url and next_url.startswith("/"):
            return next_url
        return str(self.success_url)

    def form_valid(self, form):
        table = form.save(commit=False)
        width_px, height_px = Table.DEFAULT_SIZES.get(table.shape, (68, 68))
        table.width_px, table.height_px = width_px, height_px
        table.save()
        self.object = table
        messages.success(self.request, "เพิ่มโต๊ะใหม่เรียบร้อยแล้ว")
        return redirect(self.get_success_url())


class TableUpdateView(StaffRequiredMixin, UpdateView):
    model = Table
    form_class = TableForm
    template_name = "tables/table_form.html"
    success_url = reverse_lazy("tables:manage")

    def form_valid(self, form):
        old_shape = Table.objects.filter(pk=self.object.pk).values_list("shape", flat=True).first()
        table = form.save(commit=False)
        if table.shape != old_shape:
            width_px, height_px = Table.DEFAULT_SIZES.get(table.shape, (68, 68))
            table.width_px, table.height_px = width_px, height_px
        table.save()
        self.object = table
        messages.success(self.request, f"แก้ไขโต๊ะ {self.object.table_number} เรียบร้อยแล้ว")
        return redirect(self.get_success_url())


class TableDeleteView(StaffRequiredMixin, DeleteView):
    model = Table
    success_url = reverse_lazy("tables:manage")
    template_name = "tables/table_confirm_delete.html"

    def form_valid(self, form):
        messages.success(self.request, "ลบโต๊ะเรียบร้อยแล้ว")
        return super().form_valid(form)


class TablePositionUpdateView(StaffRequiredMixin, View):
    """
    FR-23: endpoint แบบ JSON สำหรับฟีเจอร์ 'ย้ายตำแหน่ง/ปรับขนาดโต๊ะ' (ลากวาง/ลากขยายบนผังร้านในหน้า Dashboard)
    รับพิกัด pos_x, pos_y (เปอร์เซ็นต์ 0-100 เทียบกับขนาดผัง) และ/หรือ width_px, height_px (px)
    และ/หรือ shape, capacity (จากฟอร์มแก้ไขเล็กๆ ที่เด้งขึ้นตอนกดไอคอนดินสอบนโต๊ะ ในโหมดแก้ไขผังร้าน)
    แล้วบันทึกลงฐานข้อมูลทันที - ส่งมาเฉพาะคู่ที่ต้องการอัปเดตก็ได้ (ลากย้าย ส่งแค่ pos_x/pos_y,
    ลากขยาย ส่งแค่ width_px/height_px, แก้ไขรูปทรง/ที่นั่ง ส่งแค่ shape/capacity)
    """

    def post(self, request, pk):
        table = get_object_or_404(Table, pk=pk)
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "ข้อมูลไม่ถูกต้อง"}, status=400)

        update_fields = []
        if "pos_x" in data and "pos_y" in data:
            try:
                pos_x = max(0, min(100, float(data["pos_x"])))
                pos_y = max(0, min(100, float(data["pos_y"])))
            except (TypeError, ValueError):
                return JsonResponse({"error": "พิกัดไม่ถูกต้อง"}, status=400)
            table.pos_x, table.pos_y = pos_x, pos_y
            update_fields += ["pos_x", "pos_y"]

        if "width_px" in data and "height_px" in data:
            try:
                width_px = max(40, min(260, int(data["width_px"])))
                height_px = max(40, min(260, int(data["height_px"])))
            except (TypeError, ValueError):
                return JsonResponse({"error": "ขนาดไม่ถูกต้อง"}, status=400)
            table.width_px, table.height_px = width_px, height_px
            update_fields += ["width_px", "height_px"]

        if "shape" in data:
            if data["shape"] not in Table.Shape.values:
                return JsonResponse({"error": "รูปทรงไม่ถูกต้อง"}, status=400)
            table.shape = data["shape"]
            update_fields.append("shape")

        if "capacity" in data:
            try:
                capacity = int(data["capacity"])
            except (TypeError, ValueError):
                return JsonResponse({"error": "จำนวนที่นั่งไม่ถูกต้อง"}, status=400)
            if capacity < 1:
                return JsonResponse({"error": "จำนวนที่นั่งต้องอย่างน้อย 1"}, status=400)
            table.capacity = capacity
            update_fields.append("capacity")

        if not update_fields:
            return JsonResponse({"error": "ไม่มีข้อมูลให้บันทึก"}, status=400)

        table.save(update_fields=update_fields)
        return JsonResponse({
            "ok": True,
            "pos_x": table.pos_x, "pos_y": table.pos_y,
            "width_px": table.width_px, "height_px": table.height_px,
            "shape": table.shape, "capacity": table.capacity,
        })


class TableStatusUpdateView(StaffRequiredMixin, View):
    """
    FR-24: พนักงานอัปเดตสถานะโต๊ะแบบเรียลไทม์ (ว่าง/จองแล้ว/กำลังเตรียม/เสิร์ฟแล้ว)
    เรียกจากปุ่มบนผังร้านในหน้า Dashboard (คลิกที่โต๊ะ -> เลือกสถานะใหม่)
    """

    def post(self, request, pk):
        table = get_object_or_404(Table, pk=pk)
        new_status = request.POST.get("status") or json.loads(request.body or "{}").get("status")
        valid_statuses = dict(Table.Status.choices)
        if new_status not in valid_statuses:
            return JsonResponse({"error": "สถานะไม่ถูกต้อง"}, status=400)
        table.status = new_status
        table.save(update_fields=["status"])
        return JsonResponse({"ok": True, "status": new_status, "status_display": table.get_status_display()})


class TableGroupListView(StaffRequiredMixin, ListView):
    model = TableGroup
    template_name = "tables/group_list.html"
    context_object_name = "groups"
    queryset = TableGroup.objects.prefetch_related("tables")


class TableGroupCreateView(StaffRequiredMixin, CreateView):
    model = TableGroup
    form_class = TableGroupForm
    template_name = "tables/group_form.html"
    success_url = reverse_lazy("tables:group_list")

    def form_valid(self, form):
        messages.success(self.request, "สร้างชุดโต๊ะรวมใหม่เรียบร้อยแล้ว")
        return super().form_valid(form)


class TableGroupDeleteView(StaffRequiredMixin, DeleteView):
    model = TableGroup
    success_url = reverse_lazy("tables:group_list")
    template_name = "tables/group_confirm_delete.html"


def _redirect_next(request, fallback_name="dashboard:dashboard"):
    next_url = request.POST.get("next")
    if next_url and next_url.startswith("/"):
        return redirect(next_url)
    return redirect(fallback_name)


class FloorLandmarkCreateView(StaffRequiredMixin, View):
    """
    วางสิ่งกีดขวาง/จุดสำคัญ (บาร์, ทางเข้า-ออก, เวที, บาร์น้ำ, ทางหนีไฟ, บันได, แคชเชียร์) ลงบนผังร้าน
    วางตรงกลางผังก่อนด้วยขนาดเริ่มต้นตามประเภท แล้วลากจัดตำแหน่ง/ปรับขนาดภายหลังได้
    """

    def post(self, request):
        kind = request.POST.get("kind")
        if kind not in FloorLandmark.Kind.values:
            messages.error(request, "ประเภทจุดสำคัญไม่ถูกต้อง")
            return _redirect_next(request)

        width_px, height_px = FloorLandmark.DEFAULT_SIZES.get(kind, (90, 60))
        FloorLandmark.objects.create(
            kind=kind, pos_x=50, pos_y=50, width_px=width_px, height_px=height_px
        )
        messages.success(request, "เพิ่มจุดสำคัญบนผังร้านเรียบร้อยแล้ว ลากเพื่อจัดตำแหน่ง/ปรับขนาดได้เลย")
        return _redirect_next(request)


class FloorLandmarkGeometryUpdateView(StaffRequiredMixin, View):
    """endpoint แบบ JSON สำหรับลากย้ายตำแหน่ง/ลากปรับขนาดจุดสำคัญบนผังร้าน (เหมือน TablePositionUpdateView)"""

    def post(self, request, pk):
        landmark = get_object_or_404(FloorLandmark, pk=pk)
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "ข้อมูลไม่ถูกต้อง"}, status=400)

        update_fields = []
        if "pos_x" in data and "pos_y" in data:
            try:
                pos_x = max(0, min(100, float(data["pos_x"])))
                pos_y = max(0, min(100, float(data["pos_y"])))
            except (TypeError, ValueError):
                return JsonResponse({"error": "พิกัดไม่ถูกต้อง"}, status=400)
            landmark.pos_x, landmark.pos_y = pos_x, pos_y
            update_fields += ["pos_x", "pos_y"]

        if "width_px" in data and "height_px" in data:
            try:
                width_px = max(36, min(360, int(data["width_px"])))
                height_px = max(28, min(360, int(data["height_px"])))
            except (TypeError, ValueError):
                return JsonResponse({"error": "ขนาดไม่ถูกต้อง"}, status=400)
            landmark.width_px, landmark.height_px = width_px, height_px
            update_fields += ["width_px", "height_px"]

        if not update_fields:
            return JsonResponse({"error": "ไม่มีข้อมูลให้บันทึก"}, status=400)

        landmark.save(update_fields=update_fields)
        return JsonResponse({
            "ok": True,
            "pos_x": landmark.pos_x, "pos_y": landmark.pos_y,
            "width_px": landmark.width_px, "height_px": landmark.height_px,
        })


class FloorLandmarkDeleteView(StaffRequiredMixin, View):
    """ลบจุดสำคัญ - เรียกจากปุ่ม ✕ บนผังร้าน (AJAX, คืนค่า JSON) หรือจากฟอร์มปกติ (redirect กลับ) ก็ได้"""

    def post(self, request, pk):
        landmark = get_object_or_404(FloorLandmark, pk=pk)
        landmark.delete()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        messages.success(request, "ลบจุดสำคัญเรียบร้อยแล้ว")
        return _redirect_next(request)
