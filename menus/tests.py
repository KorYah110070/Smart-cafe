from django.test import TestCase
from django.urls import reverse

from .models import MenuCategory, MenuItem


class GuestCanViewMenuTests(TestCase):
    """เมนูต้องดูได้โดยไม่ต้องล็อกอิน (ตามที่ลูกค้าขอให้เปิดดูได้เลย)"""

    def test_guest_gets_200_not_redirect_to_login(self):
        resp = self.client.get(reverse("menus:menu_list"))
        self.assertEqual(resp.status_code, 200)

    def test_guest_sees_menu_item_name(self):
        category = MenuCategory.objects.create(name="เครื่องดื่ม")
        MenuItem.objects.create(category=category, name="Iced Latte", price=65, is_available=True)
        resp = self.client.get(reverse("menus:menu_list"))
        self.assertContains(resp, "Iced Latte")

    def test_menu_item_image_field_is_optional(self):
        item = MenuItem.objects.create(name="ครัวซองต์เนย", price=59)
        self.assertFalse(item.image)
