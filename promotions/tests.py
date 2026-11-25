from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from .forms import PromotionForm
from .models import Promotion


class GuestCanViewPromotionsTests(TestCase):
    """โปรโมชั่นต้องดูได้โดยไม่ต้องล็อกอิน (ตามที่ลูกค้าขอให้เปิดดูได้เลย)"""

    def test_guest_gets_200_not_redirect_to_login(self):
        resp = self.client.get(reverse("promotions:promotion_list"))
        self.assertEqual(resp.status_code, 200)

    def test_guest_sees_active_promotion_title(self):
        today = date.today()
        Promotion.objects.create(
            title="ลดราคาช่วงบ่าย",
            discount_percent=15,
            start_date=today - timedelta(days=1),
            end_date=today + timedelta(days=30),
            is_active=True,
        )
        resp = self.client.get(reverse("promotions:promotion_list"))
        self.assertContains(resp, "ลดราคาช่วงบ่าย")


class PromotionImageFieldTests(TestCase):
    """FR-26 (ส่วนขยาย): โปรโมชั่นใส่รูปภาพได้"""

    def test_model_has_optional_image_field(self):
        today = date.today()
        promo = Promotion.objects.create(
            title="ทดสอบ", start_date=today, end_date=today + timedelta(days=1)
        )
        self.assertFalse(promo.image)

    def test_form_includes_image_field(self):
        self.assertIn("image", PromotionForm.Meta.fields)
