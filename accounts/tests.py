from django.test import TestCase
from django.urls import reverse

from .models import User


class RegisterPageTests(TestCase):
    """หน้าสมัครสมาชิกแบบใหม่ (การ์ดโลโก้ Smart Cafe เหมือนหน้า Login)"""

    def test_register_page_loads(self):
        resp = self.client.get(reverse("accounts:register"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "SIGN UP")

    def test_register_creates_customer_with_optional_phone(self):
        resp = self.client.post(
            reverse("accounts:register"),
            {
                "username": "newcustomer",
                "email": "new@example.com",
                "phone_number": "",
                "password1": "SuperSecret9!",
                "password2": "SuperSecret9!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        user = User.objects.get(username="newcustomer")
        self.assertEqual(user.role, User.Role.CUSTOMER)
        self.assertEqual(user.phone_number, "")
