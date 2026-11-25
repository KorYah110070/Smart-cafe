from django.db import models


class Table(models.Model):
    """
    โต๊ะในร้าน (FR-23 การจัดการข้อมูลโต๊ะ)
    สถานะโต๊ะอ้างอิงตามสไลด์ 'รายละเอียดสถานะโต๊ะ':
      สีเทา = Available, สีส้ม = Reserved,
      สีแดง = Preparing/Waiting Order, สีเขียว = Served
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", "ว่าง (พร้อมให้จอง)"
        RESERVED = "reserved", "มีการจองโต๊ะแล้ว"
        PREPARING = "preparing", "กำลังเตรียม / รอออเดอร์"
        SERVED = "served", "เสิร์ฟแล้ว"

    class Shape(models.TextChoices):
        SQUARE = "square", "จัตุรัส"
        RECT = "rect", "ผืนผ้า"
        ROUND = "round", "กลม"

    # ขนาดเริ่มต้น (px) ตามรูปทรง ใช้ตอนสร้างโต๊ะใหม่/เปลี่ยนรูปทรง - ปรับขนาดเองภายหลังได้ด้วยการลาก
    DEFAULT_SIZES = {
        Shape.SQUARE: (68, 68),
        Shape.RECT: (108, 64),
        Shape.ROUND: (68, 68),
    }

    table_number = models.PositiveIntegerField(unique=True, verbose_name="หมายเลขโต๊ะ")
    zone = models.CharField(max_length=50, blank=True, verbose_name="โซน")
    capacity = models.PositiveIntegerField(default=4, verbose_name="จำนวนที่นั่ง (ความจุ)")
    shape = models.CharField(
        max_length=10, choices=Shape.choices, default=Shape.SQUARE, verbose_name="รูปทรงโต๊ะ"
    )
    pos_x = models.FloatField(default=0, help_text="พิกัดตำแหน่งบนผังร้าน (แกน X) สำหรับแสดงผล")
    pos_y = models.FloatField(default=0, help_text="พิกัดตำแหน่งบนผังร้าน (แกน Y) สำหรับแสดงผล")
    width_px = models.PositiveIntegerField(default=68, help_text="ความกว้างของโต๊ะบนผังร้าน (px)")
    height_px = models.PositiveIntegerField(default=68, help_text="ความสูงของโต๊ะบนผังร้าน (px)")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE)

    class Meta:
        ordering = ["table_number"]

    def __str__(self):
        return f"โต๊ะ {self.table_number} ({self.zone}) - {self.get_status_display()}"

    def is_bookable(self):
        return self.status == self.Status.AVAILABLE


class TableGroup(models.Model):
    """
    ชุดโต๊ะที่ 'รวมกันได้จริง' ในทางกายภาพ กำหนดโดยแอดมินล่วงหน้า
    ใช้สำหรับฟีเจอร์แนะนำโต๊ะอัตโนมัติเมื่อกลุ่มลูกค้าใหญ่กว่าโต๊ะเดี่ยว
    """

    group_name = models.CharField(max_length=100, verbose_name="ชื่อชุดโต๊ะ")
    tables = models.ManyToManyField(Table, related_name="groups", through="TableGroupMember")

    def total_capacity(self):
        return sum(t.capacity for t in self.tables.all())

    def all_tables_available(self):
        return all(t.status == Table.Status.AVAILABLE for t in self.tables.all())

    def __str__(self):
        table_numbers = ", ".join(str(t.table_number) for t in self.tables.all())
        return f"{self.group_name} (โต๊ะ {table_numbers})"


class TableGroupMember(models.Model):
    group = models.ForeignKey(TableGroup, on_delete=models.CASCADE)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("group", "table")


class FloorLandmark(models.Model):
    """
    สิ่งกีดขวาง/จุดสำคัญบนผังร้าน (บาร์, ทางเข้า-ออก, เวที, บาร์น้ำ, ทางหนีไฟ, บันได, แคชเชียร์)
    ไม่ใช่โต๊ะที่เปิดให้จองได้ - ใช้เพื่อวางแผนผังร้านให้ตรงกับหน้างานจริงเท่านั้น
    แสดงทั้งฝั่งแอดมิน (ลากย้าย/ปรับขนาด/ลบได้) และฝั่งลูกค้า (แสดงผลอย่างเดียว)
    """

    class Kind(models.TextChoices):
        BAR = "bar", "บาร์"
        ENTRANCE = "entrance", "ทางเข้า-ออก"
        STAGE = "stage", "เวที"
        DRINK_BAR = "drink_bar", "บาร์น้ำ"
        FIRE_ESCAPE = "fire_escape", "ทางหนีไฟ"
        STAIRS = "stairs", "บันได"
        CASHIER = "cashier", "แคชเชียร์"

    ICONS = {
        Kind.BAR: "🍸",
        Kind.ENTRANCE: "🚪",
        Kind.STAGE: "🎤",
        Kind.DRINK_BAR: "🧋",
        Kind.FIRE_ESCAPE: "🧯",
        Kind.STAIRS: "🪜",
        Kind.CASHIER: "💳",
    }

    # ขนาดเริ่มต้น (px) ตามประเภท ใช้ตอนวางใหม่ - ปรับขนาดเองภายหลังได้ด้วยการลาก
    DEFAULT_SIZES = {
        Kind.BAR: (160, 70),
        Kind.ENTRANCE: (70, 40),
        Kind.STAGE: (150, 90),
        Kind.DRINK_BAR: (110, 70),
        Kind.FIRE_ESCAPE: (60, 40),
        Kind.STAIRS: (70, 90),
        Kind.CASHIER: (80, 60),
    }

    kind = models.CharField(max_length=20, choices=Kind.choices, verbose_name="ประเภท")
    label = models.CharField(
        max_length=50, blank=True, verbose_name="ชื่อกำกับ",
        help_text="ถ้าไม่กรอกจะใช้ชื่อตามประเภทโดยอัตโนมัติ",
    )
    pos_x = models.FloatField(default=50, help_text="พิกัดตำแหน่งบนผังร้าน (แกน X) เป็นเปอร์เซ็นต์")
    pos_y = models.FloatField(default=50, help_text="พิกัดตำแหน่งบนผังร้าน (แกน Y) เป็นเปอร์เซ็นต์")
    width_px = models.PositiveIntegerField(default=90)
    height_px = models.PositiveIntegerField(default=60)

    class Meta:
        ordering = ["id"]
        verbose_name = "จุดสำคัญบนผังร้าน"
        verbose_name_plural = "จุดสำคัญบนผังร้าน"

    def icon(self):
        return self.ICONS.get(self.kind, "📍")

    def display_label(self):
        return self.label or self.get_kind_display()

    def __str__(self):
        return self.display_label()
