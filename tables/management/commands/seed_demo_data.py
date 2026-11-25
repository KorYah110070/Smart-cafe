from datetime import date, timedelta

from django.core.management.base import BaseCommand

from menus.models import MenuCategory, MenuItem
from promotions.models import Promotion
from tables.models import FloorLandmark, Table, TableGroup, TableGroupMember


class Command(BaseCommand):
    help = "สร้างข้อมูลตัวอย่าง (โต๊ะ, ชุดโต๊ะรวม, เมนู, โปรโมชั่น) เพื่อใช้ทดสอบ/สาธิตระบบ"

    def handle(self, *args, **options):
        if Table.objects.exists():
            self.stdout.write(self.style.WARNING("มีข้อมูลโต๊ะอยู่แล้ว ข้ามการสร้างข้อมูลตัวอย่าง"))
            return

        # โซน A: โต๊ะเล็ก 2 ที่นั่ง ทรงกลม (ตำแหน่ง pos_x/pos_y เป็น % บนผังร้าน ใช้แสดงผลบน Admin Dashboard)
        positions_a = [(15, 25), (30, 25), (15, 48)]
        tables_a = [
            Table.objects.create(
                table_number=n, zone="A", capacity=2, shape=Table.Shape.ROUND,
                width_px=68, height_px=68, pos_x=x, pos_y=y,
            )
            for n, (x, y) in zip(range(1, 4), positions_a)
        ]
        # โซน B: โต๊ะกลาง 4 ที่นั่ง ทรงจัตุรัส (ใช้ทำชุดรวมได้)
        t4 = Table.objects.create(
            table_number=4, zone="B", capacity=4, shape=Table.Shape.SQUARE,
            width_px=68, height_px=68, pos_x=48, pos_y=25,
        )
        t11 = Table.objects.create(
            table_number=11, zone="B", capacity=4, shape=Table.Shape.SQUARE,
            width_px=68, height_px=68, pos_x=63, pos_y=25,
        )
        t12 = Table.objects.create(
            table_number=12, zone="B", capacity=4, shape=Table.Shape.SQUARE,
            width_px=68, height_px=68, pos_x=63, pos_y=48,
        )
        # โซน C: โต๊ะใหญ่ 6-8 ที่นั่ง ทรงผืนผ้า
        Table.objects.create(
            table_number=20, zone="C", capacity=6, shape=Table.Shape.RECT,
            width_px=108, height_px=64, pos_x=82, pos_y=25,
        )
        Table.objects.create(
            table_number=21, zone="C", capacity=8, shape=Table.Shape.RECT,
            width_px=108, height_px=64, pos_x=82, pos_y=52,
        )

        # สิ่งกีดขวาง/จุดสำคัญบนผังร้าน (วางรอบขอบผัง ไม่ทับโต๊ะ)
        landmark_layout = [
            (FloorLandmark.Kind.ENTRANCE, 6, 8),
            (FloorLandmark.Kind.CASHIER, 6, 25),
            (FloorLandmark.Kind.BAR, 48, 8),
            (FloorLandmark.Kind.STAGE, 90, 8),
            (FloorLandmark.Kind.DRINK_BAR, 6, 85),
            (FloorLandmark.Kind.STAIRS, 90, 85),
            (FloorLandmark.Kind.FIRE_ESCAPE, 48, 90),
        ]
        for kind, x, y in landmark_layout:
            width_px, height_px = FloorLandmark.DEFAULT_SIZES.get(kind, (90, 60))
            FloorLandmark.objects.create(
                kind=kind, pos_x=x, pos_y=y, width_px=width_px, height_px=height_px
            )

        group = TableGroup.objects.create(group_name="ชุดรวมโซน B (4+11)")
        TableGroupMember.objects.create(group=group, table=t4)
        TableGroupMember.objects.create(group=group, table=t11)

        group2 = TableGroup.objects.create(group_name="ชุดรวมโซน B (11+12)")
        TableGroupMember.objects.create(group=group2, table=t11)
        TableGroupMember.objects.create(group=group2, table=t12)

        coffee = MenuCategory.objects.create(name="เครื่องดื่มกาแฟ")
        non_coffee = MenuCategory.objects.create(name="เครื่องดื่ม Non-Coffee")
        food = MenuCategory.objects.create(name="อาหารทานเล่น")

        MenuItem.objects.create(category=coffee, name="Espresso", price=55)
        MenuItem.objects.create(category=coffee, name="Iced Latte", price=65, is_recommended=True)
        MenuItem.objects.create(category=non_coffee, name="Espresso Yuzu Soda", price=85, is_recommended=True)
        MenuItem.objects.create(category=food, name="ครัวซองต์เนย", price=59)

        today = date.today()
        Promotion.objects.create(
            title="ลดราคาช่วงบ่าย",
            description="ลดเครื่องดื่มทุกแก้ว 15% ช่วง 14:00-16:00",
            discount_percent=15,
            start_date=today,
            end_date=today + timedelta(days=30),
        )

        self.stdout.write(self.style.SUCCESS("สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว"))
