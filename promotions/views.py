from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import PromotionForm
from .models import Promotion


class PromotionListView(ListView):
    """FR-26: ดูโปรโมชั่น (ผู้เยี่ยมชมที่ยังไม่ล็อกอินก็ดูได้เลย)"""

    model = Promotion
    template_name = "promotions/promotion_list.html"
    context_object_name = "promotions"

    def get_queryset(self):
        today = timezone.localdate()
        return Promotion.objects.filter(
            is_active=True, start_date__lte=today, end_date__gte=today
        )


class PromotionManageListView(StaffRequiredMixin, ListView):
    """หน้า 'จัดการโปรโมชั่น' ของแอดมิน/พนักงาน - เห็นโปรโมชั่นทั้งหมดรวมที่หมดอายุ/ปิดอยู่"""

    model = Promotion
    template_name = "promotions/manage_list.html"
    context_object_name = "promotions"
    queryset = Promotion.objects.all().order_by("-start_date")


class PromotionCreateView(StaffRequiredMixin, CreateView):
    model = Promotion
    form_class = PromotionForm
    template_name = "promotions/promotion_form.html"
    success_url = reverse_lazy("promotions:manage")

    def form_valid(self, form):
        messages.success(self.request, "เพิ่มโปรโมชั่นใหม่เรียบร้อยแล้ว")
        return super().form_valid(form)


class PromotionUpdateView(StaffRequiredMixin, UpdateView):
    model = Promotion
    form_class = PromotionForm
    template_name = "promotions/promotion_form.html"
    success_url = reverse_lazy("promotions:manage")

    def form_valid(self, form):
        messages.success(self.request, "แก้ไขโปรโมชั่นเรียบร้อยแล้ว")
        return super().form_valid(form)


class PromotionDeleteView(StaffRequiredMixin, DeleteView):
    model = Promotion
    success_url = reverse_lazy("promotions:manage")
    template_name = "promotions/promotion_confirm_delete.html"
