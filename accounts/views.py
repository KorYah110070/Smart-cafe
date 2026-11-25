from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView

from .forms import CafeAuthenticationForm, RegisterForm, StaffCreateForm
from .mixins import StaffRequiredMixin
from .models import User


class RegisterView(CreateView):
    """FR-01: สมัครสมาชิก"""

    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("tables:floor_plan")

    def form_valid(self, form):
        response = super().form_valid(form)
        # ต้องระบุ backend ตรง ๆ เพราะตอนนี้มีมากกว่า 1 authentication backend
        # (เพิ่ม allauth เข้ามาสำหรับ Google Login) login() เดาเองไม่ได้ว่าจะใช้ backend ไหน
        login(self.request, self.object, backend="django.contrib.auth.backends.ModelBackend")
        return response


class CafeLoginView(LoginView):
    """
    FR-02: เข้าสู่ระบบ
    รองรับ "จดจำการเข้าสู่ระบบ": ถ้าติ๊ก (ค่าเริ่มต้น) เซสชันจะอยู่นาน 14 วันตามปกติ
    ถ้าไม่ติ๊ก เซสชันจะหมดอายุทันทีที่ปิดเบราว์เซอร์
    """

    template_name = "accounts/login.html"
    authentication_form = CafeAuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # ปุ่ม "เข้าสู่ระบบด้วย Google" จะโผล่เองอัตโนมัติเมื่อตั้งค่า GOOGLE_OAUTH_CLIENT_ID/SECRET
        # จริงแล้ว (ดูหมายเหตุใน config/settings.py) - ตอนนี้ยังเป็นแค่โครง ยังไม่ใส่ค่าจริง
        context["google_login_enabled"] = settings.GOOGLE_LOGIN_ENABLED
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.POST.get("remember_me"):
            self.request.session.set_expiry(1209600)  # 14 วัน (ค่าเริ่มต้นของ Django)
        else:
            self.request.session.set_expiry(0)  # หมดอายุเมื่อปิดเบราว์เซอร์
        return response


class CafeLogoutView(LogoutView):
    """FR-03: ออกจากระบบ"""

    next_page = reverse_lazy("accounts:login")


class MemberListView(StaffRequiredMixin, ListView):
    """
    หน้า 'จัดการสมาชิก' ของแอดมิน/พนักงาน - ดูรายชื่อผู้ใช้งานทั้งหมดในระบบ
    พร้อมจำนวนการจองสะสมของแต่ละคน, สลับสถานะใช้งาน/ระงับบัญชีได้
    """

    model = User
    template_name = "accounts/member_list.html"
    context_object_name = "members"
    paginate_by = 30

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")
        role_filter = self.request.GET.get("role")
        search = self.request.GET.get("q")
        if role_filter:
            qs = qs.filter(role=role_filter)
        if search:
            qs = qs.filter(username__icontains=search)
        return qs.prefetch_related("reservations")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["role_choices"] = User.Role.choices
        context["selected_role"] = self.request.GET.get("role", "")
        context["search_query"] = self.request.GET.get("q", "")
        context["total_customers"] = User.objects.filter(role=User.Role.CUSTOMER).count()
        context["total_staff"] = User.objects.filter(role=User.Role.STAFF).count()
        return context


class MemberCreateView(StaffRequiredMixin, CreateView):
    """หน้า '+ เพิ่มพนักงาน' - แอดมิน/พนักงานสร้างบัญชีพนักงานเสิร์ฟ (หรือแอดมินคนใหม่) ได้โดยตรง
    โดยกรอก อีเมล/ชื่อผู้ใช้/รหัสผ่าน แทนที่จะต้องให้คนนั้นไปสมัครสมาชิกเองแล้วมาเปลี่ยนบทบาทภายหลัง"""

    form_class = StaffCreateForm
    template_name = "accounts/member_form.html"
    success_url = reverse_lazy("accounts:member_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(
            self.request,
            f"เพิ่มบัญชี {self.object.username} ({self.object.get_role_display()}) เรียบร้อยแล้ว",
        )
        return response


class MemberToggleActiveView(StaffRequiredMixin, View):
    """เปิด/ปิดการใช้งานบัญชีสมาชิก (is_active) จากหน้าจัดการสมาชิก"""

    def post(self, request, pk):
        member = get_object_or_404(User, pk=pk)
        if member == request.user:
            messages.error(request, "ไม่สามารถระงับบัญชีของตัวเองได้")
            return redirect("accounts:member_list")
        member.is_active = not member.is_active
        member.save(update_fields=["is_active"])
        state = "เปิดใช้งาน" if member.is_active else "ระงับการใช้งาน"
        messages.success(request, f"{state}บัญชีของ {member.username} เรียบร้อยแล้ว")
        return redirect("accounts:member_list")


class MemberRoleUpdateView(StaffRequiredMixin, View):
    """เปลี่ยนบทบาทผู้ใช้งาน (ลูกค้า/พนักงาน/แอดมิน) จากหน้าจัดการสมาชิก"""

    def post(self, request, pk):
        member = get_object_or_404(User, pk=pk)
        new_role = request.POST.get("role")
        if new_role not in dict(User.Role.choices):
            messages.error(request, "บทบาทไม่ถูกต้อง")
            return redirect("accounts:member_list")
        member.role = new_role
        member.save(update_fields=["role"])
        messages.success(request, f"เปลี่ยนบทบาทของ {member.username} เป็น {member.get_role_display()} แล้ว")
        return redirect("accounts:member_list")
