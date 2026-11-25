from django.db import models


class SiteSettings(models.Model):
    """
    ตั้งค่าระบบ (FR-28 แนวคิด): ข้อมูลร้าน ใช้แบบ Singleton (มีแถวเดียวในระบบเสมอ)
    เรียกใช้ผ่าน SiteSettings.load() เพื่อให้ได้ object เดียวกันเสมอ (สร้างอัตโนมัติถ้ายังไม่มี)
    """

    cafe_name = models.CharField(max_length=100, default="Smart Cafe")
    description = models.TextField(
        blank=True, help_text="คำอธิบายสั้น ๆ เกี่ยวกับร้าน แสดงในหน้าแรก/เกี่ยวกับเรา"
    )
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    opening_time = models.TimeField(default="08:00")
    closing_time = models.TimeField(default="20:00")
    logo = models.ImageField(upload_to="site/", blank=True, null=True, verbose_name="โลโก้ร้าน")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "ตั้งค่าระบบ"
        verbose_name_plural = "ตั้งค่าระบบ"

    def __str__(self):
        return self.cafe_name

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
