from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView

from accounts.mixins import StaffRequiredMixin
from menus.models import MenuItem
from reservations.models import Reservation

from .models import Order, OrderItem


class OrderListView(LoginRequiredMixin, ListView):
    """
    FR-14: ผู้ใช้สามารถตรวจสอบสถานะคำสั่งซื้อได้ (ลูกค้าเห็นเฉพาะออเดอร์ของตัวเอง อ่านอย่างเดียว)
    FR-19, FR-20: พนักงาน/แอดมินเห็นออเดอร์ทั้งหมด และเปลี่ยนสถานะได้โดยตรงจากหน้านี้ (เหมือน "จัดการการจอง")
    """

    model = Order
    template_name = "orders/order_list.html"
    context_object_name = "orders"

    def get_queryset(self):
        user = self.request.user
        if user.is_staff_member or user.is_admin_role or user.is_superuser:
            return Order.objects.all().select_related("customer", "reservation").prefetch_related("items")
        return Order.objects.filter(customer=user).prefetch_related("items")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        is_staff_view = bool(user.is_staff_member or user.is_admin_role or user.is_superuser)
        context["is_staff_view"] = is_staff_view
        context["layout_template"] = "dashboard/base_admin.html" if is_staff_view else "base.html"
        context["status_choices"] = Order.Status.choices
        return context


def _create_order_items(order, post_data):
    """สร้าง OrderItem จากฟิลด์ qty_<menu_item_id> ในฟอร์ม - ใช้ร่วมกันทั้งฝั่งลูกค้าสั่งเองและพนักงานสั่งแทน"""
    created_any = False
    for key, value in post_data.items():
        if not key.startswith("qty_"):
            continue
        try:
            quantity = int(value)
        except ValueError:
            continue
        if quantity <= 0:
            continue
        menu_item_id = key.replace("qty_", "")
        menu_item = MenuItem.objects.filter(id=menu_item_id).first()
        if not menu_item:
            continue
        OrderItem.objects.create(
            order=order, menu_item=menu_item, quantity=quantity, unit_price=menu_item.price
        )
        created_any = True
    return created_any


def _get_payment_method(request):
    """
    ตรวจสอบวิธีชำระเงินที่ส่งมาจากฟอร์ม - ตามนโยบาย "ซื้อปุ๊บจ่ายปั๊บ" ที่อาจารย์ที่ปรึกษาแนะนำ
    ทุกออเดอร์ต้องระบุวิธีชำระเงินตั้งแต่ตอนสั่งเลย คืนค่า None ถ้าไม่ได้เลือก/เลือกไม่ถูกต้อง
    """
    pm = request.POST.get("payment_method")
    if pm not in dict(Order.PaymentMethod.choices):
        return None
    return pm


class CreateOrderView(LoginRequiredMixin, View):
    """FR-11 ถึง FR-13: เพิ่มสินค้าลงตะกร้าและยืนยันคำสั่งซื้อ (ทำแบบฟอร์มเดียวจบเพื่อความง่าย)
    ลูกค้าต้องเลือกวิธีชำระเงินตอนสั่งเลย (ซื้อปุ๊บจ่ายปั๊บ) จึงถือว่าชำระเงินแล้วทันทีที่สั่งสำเร็จ"""

    template_name = "orders/create_order.html"

    def get(self, request, reservation_id):
        reservation = get_object_or_404(
            Reservation, pk=reservation_id, customer=request.user
        )
        menu_items = MenuItem.objects.filter(is_available=True)
        return render(
            request,
            self.template_name,
            {
                "reservation": reservation, "menu_items": menu_items,
                "is_staff_view": False, "layout_template": "base.html",
                "payment_choices": Order.PaymentMethod.choices,
            },
        )

    def post(self, request, reservation_id):
        reservation = get_object_or_404(
            Reservation, pk=reservation_id, customer=request.user
        )
        payment_method = _get_payment_method(request)
        if not payment_method:
            messages.error(request, "กรุณาเลือกวิธีชำระเงิน")
            return redirect("orders:create", reservation_id=reservation.id)

        order = Order.objects.create(
            reservation=reservation,
            customer=request.user,
            order_type=Order.OrderType.DINE_IN,
            payment_method=payment_method,
            is_paid=True,
        )

        if not _create_order_items(order, request.POST):
            order.delete()
            messages.error(request, "กรุณาเลือกสินค้าอย่างน้อย 1 รายการ")
            return redirect("orders:create", reservation_id=reservation.id)

        messages.success(request, "สั่งซื้อและชำระเงินสำเร็จ")
        return redirect("orders:my_orders")


class StaffCreateOrderView(StaffRequiredMixin, View):
    """
    พนักงาน/แอดมินสั่งเมนูแทนลูกค้า - ใช้กับลูกค้าวอล์กอิน (ไม่มีบัญชี) เป็นหลัก
    แต่เรียกได้กับการจองใดก็ได้ (ไม่จำกัดว่าต้องเป็นของ request.user)
    ต้องเลือกวิธีชำระเงินตอนสั่งเช่นกัน (ซื้อปุ๊บจ่ายปั๊บ)
    """

    template_name = "orders/create_order.html"

    def get(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        menu_items = MenuItem.objects.filter(is_available=True)
        return render(
            request,
            self.template_name,
            {
                "reservation": reservation, "menu_items": menu_items,
                "is_staff_view": True, "layout_template": "dashboard/base_admin.html",
                "payment_choices": Order.PaymentMethod.choices,
            },
        )

    def post(self, request, reservation_id):
        reservation = get_object_or_404(Reservation, pk=reservation_id)
        payment_method = _get_payment_method(request)
        if not payment_method:
            messages.error(request, "กรุณาเลือกวิธีชำระเงิน")
            return redirect("orders:staff_create", reservation_id=reservation.id)

        order = Order.objects.create(
            reservation=reservation,
            customer=reservation.customer,
            order_type=Order.OrderType.DINE_IN,
            payment_method=payment_method,
            is_paid=True,
        )

        if not _create_order_items(order, request.POST):
            order.delete()
            messages.error(request, "กรุณาเลือกสินค้าอย่างน้อย 1 รายการ")
            return redirect("orders:staff_create", reservation_id=reservation.id)

        messages.success(
            request, f"บันทึกคำสั่งซื้อให้ {reservation.customer_display_name} เรียบร้อยแล้ว"
        )
        return redirect("orders:my_orders")


class TakeawayCreateOrderView(StaffRequiredMixin, View):
    """
    FR ใหม่ตามคำแนะนำอาจารย์ที่ปรึกษา: ปุ่ม "ซื้อกลับ" ให้พนักงาน/แอดมินคีย์ขายหน้าร้านได้เลย
    ไม่ผูกกับโต๊ะ/ไม่ต้องมีการจอง สั่ง-จ่าย-จบในหน้าเดียว (ซื้อปุ๊บจ่ายปั๊บ)
    """

    template_name = "orders/takeaway_form.html"

    def get(self, request):
        menu_items = MenuItem.objects.filter(is_available=True)
        return render(
            request,
            self.template_name,
            {"menu_items": menu_items, "payment_choices": Order.PaymentMethod.choices},
        )

    def post(self, request):
        payment_method = _get_payment_method(request)
        if not payment_method:
            messages.error(request, "กรุณาเลือกวิธีชำระเงิน")
            return redirect("orders:takeaway_create")

        guest_name = request.POST.get("guest_name", "").strip()
        order = Order.objects.create(
            reservation=None,
            customer=None,
            order_type=Order.OrderType.TAKEAWAY,
            guest_name=guest_name,
            payment_method=payment_method,
            is_paid=True,
        )

        if not _create_order_items(order, request.POST):
            order.delete()
            messages.error(request, "กรุณาเลือกสินค้าอย่างน้อย 1 รายการ")
            return redirect("orders:takeaway_create")

        messages.success(
            request, f"บันทึกการขายซื้อกลับ #{order.id} เรียบร้อยแล้ว (รวม {order.total_price()} บาท)"
        )
        return redirect("orders:my_orders")


class AdminOrderStatusUpdateView(StaffRequiredMixin, View):
    """เปลี่ยนสถานะคำสั่งซื้อจากหน้า 'จัดการคำสั่งซื้อ' (ปุ่ม/ดรอปดาวน์ในแต่ละแถว) - FR-20"""

    success_url = reverse_lazy("orders:my_orders")

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        new_status = request.POST.get("status")
        if new_status in dict(Order.Status.choices):
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"อัปเดตสถานะออเดอร์ #{order.id} เรียบร้อยแล้ว")
        else:
            messages.error(request, "สถานะไม่ถูกต้อง")
        return redirect(self.success_url)
