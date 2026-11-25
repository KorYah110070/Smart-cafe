from django.conf import settings
from django.db import models

from tables.models import Table


class Reservation(models.Model):
    """
    การจองโต๊ะ (FR-06, FR-07, FR-28 ถึง FR-33)
    หมายเหตุสำคัญ: Reservation ไม่ผูกกับ Table แบบ 1:1 อีกต่อไป
    แต่ผูกผ่าน ReservationTable (many-to-many) เพื่อรองรับทั้งโต๊ะเดี่ยวและโต๊ะรวมหลายตัว
    """

    class Status(models.TextChoices):
        RESERVED = "reserved", "จองแล้ว (รอลูกค้ามาถึง)"
        PREPARING = "preparing", "กำลังเตรียม / รอออเดอร์"
        SERVED = "served", "เสิร์ฟแล้ว"
        COMPLETED = "completed", "เสร็จสมบูรณ์"
        CANCELLED = "cancelled", "ยกเลิกแล้ว"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reservations",
        null=True,
        blank=True,
    )
    guest_name = models.CharField(
        max_length=150, blank=True, verbose_name="ชื่อลูกค้า (วอล์กอิน)"
    )
    is_walkin = models.BooleanField(
        default=False, verbose_name="ลูกค้าวอล์กอิน (ไม่ได้จองล่วงหน้า/ไม่มีบัญชีสมาชิก)"
    )
    tables = models.ManyToManyField(Table, through="ReservationTable", related_name="reservations")

    party_size = models.PositiveIntegerField(verbose_name="จำนวนคน")
    reservation_date = models.DateField(verbose_name="วันที่จอง")

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RESERVED)

    extra_chair_requested = models.BooleanField(default=False, verbose_name="ขอเก้าอี้เพิ่มเติม")
    extra_table_requested = models.BooleanField(default=False, verbose_name="ขอโต๊ะเสริม")

    edit_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-reservation_date", "-created_at"]

    def __str__(self):
        return f"การจองของ {self.customer_display_name} วันที่ {self.reservation_date} ({self.party_size} คน)"

    @property
    def customer_display_name(self):
        """ชื่อลูกค้าที่ใช้แสดงผล - ลูกค้าสมาชิกใช้ username, ลูกค้าวอล์กอินใช้ guest_name ที่พนักงานกรอกไว้"""
        if self.customer_id:
            return self.customer.username
        return self.guest_name or "ลูกค้าวอล์กอิน"

    def is_editable(self):
        """แก้ไขได้เฉพาะตอนที่ยังไม่ถึงร้าน (ตาม Business Rule ข้อ 4 ที่เพิ่มใหม่)"""
        return self.status == self.Status.RESERVED

    def is_combined(self):
        return self.tables.count() > 1

    def table_numbers_display(self):
        return ", ".join(str(t.table_number) for t in self.tables.all())


class ReservationTable(models.Model):
    """ตารางกลาง เชื่อม Reservation <-> Table แบบ many-to-many"""

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("reservation", "table")


class ReservationHistory(models.Model):
    """Audit log สำหรับการแก้ไขการจอง (ใช้ตรวจสอบย้อนหลัง และเป็นข้อมูลให้ AI ตอบคำถามลูกค้าได้ในอนาคต)"""

    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="history"
    )
    field_changed = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.reservation_id}: {self.field_changed} {self.old_value} -> {self.new_value}"
