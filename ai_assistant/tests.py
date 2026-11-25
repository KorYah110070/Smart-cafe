import json

from django.test import TestCase
from django.urls import reverse


class GuestCanUseChatbotTests(TestCase):
    """แชทบอทต้องใช้ได้โดยไม่ต้องล็อกอิน (ตามที่ลูกค้าขอให้เปิดใช้ได้เลย)"""

    def test_guest_can_open_full_chat_page(self):
        resp = self.client.get(reverse("ai_assistant:chat"))
        self.assertEqual(resp.status_code, 200)

    def test_guest_can_call_chat_api(self):
        resp = self.client.post(
            reverse("ai_assistant:chat_api"),
            data=json.dumps({"question": "มีโต๊ะว่างไหม"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("answer", resp.json())
