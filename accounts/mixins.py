from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    ใช้จำกัดสิทธิ์หน้าฝั่งจัดการร้าน (Admin/Staff Panel) ให้เข้าถึงได้เฉพาะ
    พนักงาน (staff), แอดมิน (admin) หรือ Django superuser เท่านั้น
    ลูกค้าทั่วไปที่พยายามเข้าหน้านี้จะโดน redirect ไปหน้า login (ถ้ายังไม่ล็อกอิน)
    หรือเจอหน้า 403 (ถ้าล็อกอินแล้วแต่ไม่มีสิทธิ์)
    """

    raise_exception_for_authenticated = True

    def test_func(self):
        user = self.request.user
        return bool(
            user.is_authenticated
            and (user.is_staff_member or user.is_admin_role or user.is_superuser)
        )

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied("หน้านี้สำหรับพนักงาน/แอดมินเท่านั้น")
        return super().handle_no_permission()


class AdminOnlyMixin(StaffRequiredMixin):
    """เข้มกว่า StaffRequiredMixin อีกขั้น: เฉพาะ admin หรือ superuser (ไม่รวม staff ทั่วไป)"""

    def test_func(self):
        user = self.request.user
        return bool(user.is_authenticated and (user.is_admin_role or user.is_superuser))
