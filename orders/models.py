from django.conf import settings
from django.db import models

from menus.models import MenuItem
from reservations.models import Reservation


class Order(models.Model):
    """FR-11 ถึง FR-14, FR-19, FR-20: การสั่งซื้อสินค้า

    ตามคำแนะนำของอาจารย์ที่ปรึกษา: ระบบใช้โมเดล "ซื้อปุ๊บจ่ายปั๊บ" คือจ่ายเงินทันทีตอนสั่ง
    ไม่ใช่สั่งก่อนแล้วมาเก็บเงินทีหลัง จึงมีฟิลด์ is_paid/payment_method บันทึกไว้ตั้งแต่สร้างออเดอร์
    และรองรับ "ซื้อกลับ" (ไม่ผูกกับโต๊ะ/การจอง) นอกเหนือจากออเดอร์แบบทานที่ร้านเดิม
    """

    class Status(models.TextChoices):
        PENDING = "pending", "รอดำเนินการ"
        CONFIRMED = "confirmed", "ยืนยันแล้ว"
        PREPARING = "preparing", "กำลังเตรียม"
        SERVED = "served", "เสิร์ฟแล้ว"

    class OrderType(models.TextChoices):
        DINE_IN = "dine_in", "ทานที่ร้าน"
        TAKEAWAY = "takeaway", "ซื้อกลับ"

    class PaymentMethod(models.TextChoices):
        CASH = "cash", "เงินสด"
        TRANSFER = "transfer", "โอน/พร้อมเพย์"
        CARD = "card", "บัตร"

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="orders", null=True, blank=True
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True
    )
    order_type = models.CharField(
        max_length=10, choices=OrderType.choices, default=OrderType.DINE_IN
    )
    guest_name = models.CharField(
        max_length=150, blank=True, verbose_name="ชื่อลูกค้า (ออเดอร์ซื้อกลับ)"
    )
    is_paid = models.BooleanField(default=True, verbose_name="ชำระเงินแล้ว")
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethod.choices, blank=True, verbose_name="วิธีชำระเงิน"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def total_price(self):
        return sum(item.subtotal() for item in self.items.all())

    @property
    def customer_display_name(self):
        """
        ชื่อลูกค้าที่ใช้แสดงผล:
        - ลูกค้าสมาชิกที่ล็อกอิน -> username
        - ออเดอร์ที่ผูกกับการจอง (ทานที่ร้าน/วอล์กอิน) -> ชื่อจากการจองนั้น
        - ออเดอร์ซื้อกลับที่ไม่มีการจอง -> guest_name ที่พนักงานกรอกไว้
        """
        if self.customer_id:
            return self.customer.username
        if self.reservation_id:
            return self.reservation.customer_display_name
        return self.guest_name or "ลูกค้าซื้อกลับ"

    def __str__(self):
        return f"ออเดอร์ #{self.id} ({self.get_status_display()})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"
