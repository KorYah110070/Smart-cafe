from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    ผู้ใช้งานระบบ แบ่งบทบาทตาม Use-Case Diagram เดิม:
    - customer: ลูกค้า (ผู้ใช้ทั่วไปที่สมัครสมาชิก)
    - staff: พนักงานเสิร์ฟ
    - admin: ผู้ดูแลระบบ
    """

    class Role(models.TextChoices):
        CUSTOMER = "customer", "ลูกค้า"
        STAFF = "staff", "พนักงาน"
        ADMIN = "admin", "แอดมิน"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone_number = models.CharField(max_length=20, blank=True)

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER

    @property
    def is_staff_member(self):
        return self.role == self.Role.STAFF

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
