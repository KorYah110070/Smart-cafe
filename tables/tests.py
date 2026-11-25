"""
Unit tests สำหรับฟีเจอร์ 'แก้ไขผังร้าน' (รูปทรงโต๊ะ + สิ่งกีดขวาง/จุดสำคัญบนผังร้าน)
รันด้วยคำสั่ง: python manage.py test tables
"""

import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import FloorLandmark, Table


class TableShapeDefaultSizeTests(TestCase):
    """ตรวจสอบว่าโต๊ะใหม่ได้ขนาดเริ่มต้น (width_px/height_px) ตามรูปทรงที่เลือกโดยอัตโนมัติ"""

    def setUp(self):
        self.admin = User.objects.create_user(
            "admin1", "admin1@example.com", "pass12345", role=User.Role.ADMIN
        )
        self.client.force_login(self.admin)

    def test_create_round_table_gets_round_default_size(self):
        self.client.post(
            reverse("tables:table_add"),
            {"table_number": 101, "zone": "A", "capacity": 2, "shape": Table.Shape.ROUND, "status": "available"},
        )
        table = Table.objects.get(table_number=101)
        self.assertEqual(table.shape, Table.Shape.ROUND)
        self.assertEqual((table.width_px, table.height_px), Table.DEFAULT_SIZES[Table.Shape.ROUND])

    def test_create_rect_table_gets_wider_default_size(self):
        self.client.post(
            reverse("tables:table_add"),
            {"table_number": 102, "zone": "C", "capacity": 8, "shape": Table.Shape.RECT, "status": "available"},
        )
        table = Table.objects.get(table_number=102)
        width, height = Table.DEFAULT_SIZES[Table.Shape.RECT]
        self.assertEqual(table.width_px, width)
        self.assertGreater(table.width_px, table.height_px)

    def test_changing_shape_resets_to_new_default_size(self):
        table = Table.objects.create(table_number=103, zone="B", capacity=4, shape=Table.Shape.SQUARE)
        table.width_px, table.height_px = 68, 68
        table.save()
        self.client.post(
            reverse("tables:table_edit", args=[table.pk]),
            {"table_number": 103, "zone": "B", "capacity": 4, "shape": Table.Shape.ROUND, "status": "available"},
        )
        table.refresh_from_db()
        self.assertEqual(table.shape, Table.Shape.ROUND)
        self.assertEqual((table.width_px, table.height_px), Table.DEFAULT_SIZES[Table.Shape.ROUND])


class FloorLandmarkTests(TestCase):
    """FR-23 (ส่วนขยาย): วาง/ลากย้าย/ปรับขนาด/ลบ สิ่งกีดขวางและจุดสำคัญบนผังร้าน"""

    def setUp(self):
        self.admin = User.objects.create_user(
            "admin2", "admin2@example.com", "pass12345", role=User.Role.ADMIN
        )
        self.customer = User.objects.create_user(
            "cust1", "cust1@example.com", "pass12345", role=User.Role.CUSTOMER
        )

    def test_staff_can_place_a_landmark_with_kind_default_size(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("tables:landmark_add"), {"kind": FloorLandmark.Kind.STAGE})
        landmark = FloorLandmark.objects.get(kind=FloorLandmark.Kind.STAGE)
        self.assertEqual(
            (landmark.width_px, landmark.height_px),
            FloorLandmark.DEFAULT_SIZES[FloorLandmark.Kind.STAGE],
        )

    def test_invalid_kind_is_rejected(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("tables:landmark_add"), {"kind": "not-a-real-kind"})
        self.assertEqual(FloorLandmark.objects.count(), 0)

    def test_customer_cannot_place_a_landmark(self):
        self.client.force_login(self.customer)
        resp = self.client.post(reverse("tables:landmark_add"), {"kind": FloorLandmark.Kind.BAR})
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(FloorLandmark.objects.count(), 0)

    def test_drag_updates_position_clamped_to_0_100(self):
        self.client.force_login(self.admin)
        landmark = FloorLandmark.objects.create(kind=FloorLandmark.Kind.CASHIER, pos_x=50, pos_y=50)
        resp = self.client.post(
            reverse("tables:landmark_geometry_update", args=[landmark.pk]),
            data=json.dumps({"pos_x": 150, "pos_y": -20}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        landmark.refresh_from_db()
        self.assertEqual(landmark.pos_x, 100)
        self.assertEqual(landmark.pos_y, 0)

    def test_resize_updates_width_and_height(self):
        self.client.force_login(self.admin)
        landmark = FloorLandmark.objects.create(
            kind=FloorLandmark.Kind.STAIRS, width_px=70, height_px=90
        )
        resp = self.client.post(
            reverse("tables:landmark_geometry_update", args=[landmark.pk]),
            data=json.dumps({"width_px": 120, "height_px": 140}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        landmark.refresh_from_db()
        self.assertEqual((landmark.width_px, landmark.height_px), (120, 140))

    def test_delete_removes_landmark_and_returns_json_for_ajax(self):
        self.client.force_login(self.admin)
        landmark = FloorLandmark.objects.create(kind=FloorLandmark.Kind.FIRE_ESCAPE)
        resp = self.client.post(
            reverse("tables:landmark_delete", args=[landmark.pk]),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"ok": True})
        self.assertFalse(FloorLandmark.objects.filter(pk=landmark.pk).exists())

    def test_display_label_falls_back_to_kind_name(self):
        landmark = FloorLandmark.objects.create(kind=FloorLandmark.Kind.DRINK_BAR)
        self.assertEqual(landmark.display_label(), "บาร์น้ำ")
        landmark.label = "บาร์น้ำผลไม้"
        self.assertEqual(landmark.display_label(), "บาร์น้ำผลไม้")


class FloorPlanCustomerViewShowsLandmarksTests(TestCase):
    """หน้าแรกของลูกค้าต้องเห็นจุดสำคัญบนผังร้านด้วย (ไม่ใช่แค่ฝั่งแอดมิน)"""

    def test_guest_can_see_landmarks_on_floor_plan(self):
        FloorLandmark.objects.create(kind=FloorLandmark.Kind.ENTRANCE, label="ทางเข้าหลัก")
        resp = self.client.get(reverse("tables:floor_plan"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "ทางเข้าหลัก")
