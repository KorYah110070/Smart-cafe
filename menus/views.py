from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import MenuCategoryForm, MenuItemForm
from .models import MenuCategory, MenuItem


class MenuListView(ListView):
    """
    FR-10: ผู้ใช้ (รวมผู้เยี่ยมชมที่ยังไม่ล็อกอิน) สามารถดูรายการอาหารและเครื่องดื่มได้เลย
    เรียงเมนูแนะนำ (is_recommended) ไว้บนสุดเสมอ - ใช้เป็นหน้าเดียวกับที่ลิงก์
    "แนะนำเมนู" บน sidebar หน้าแรกชี้มา
    """

    model = MenuItem
    template_name = "menus/menu_list.html"
    context_object_name = "items"
    queryset = (
        MenuItem.objects.filter(is_available=True)
        .select_related("category")
        .order_by("-is_recommended", "category__name", "name")
    )


class MenuManageListView(StaffRequiredMixin, ListView):
    """FR-25: หน้า 'จัดการเมนู' ของแอดมิน/พนักงาน - เห็นเมนูทั้งหมดรวมที่ปิดการขาย"""

    model = MenuItem
    template_name = "menus/manage_list.html"
    context_object_name = "items"
    queryset = MenuItem.objects.all().select_related("category").order_by("category__name", "name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = MenuCategory.objects.all()
        return context


class MenuItemCreateView(StaffRequiredMixin, CreateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = "menus/menu_form.html"
    success_url = reverse_lazy("menus:manage")

    def form_valid(self, form):
        messages.success(self.request, "เพิ่มเมนูใหม่เรียบร้อยแล้ว")
        return super().form_valid(form)


class MenuItemUpdateView(StaffRequiredMixin, UpdateView):
    model = MenuItem
    form_class = MenuItemForm
    template_name = "menus/menu_form.html"
    success_url = reverse_lazy("menus:manage")

    def form_valid(self, form):
        messages.success(self.request, "แก้ไขเมนูเรียบร้อยแล้ว")
        return super().form_valid(form)


class MenuItemDeleteView(StaffRequiredMixin, DeleteView):
    model = MenuItem
    success_url = reverse_lazy("menus:manage")
    template_name = "menus/menu_confirm_delete.html"


class MenuCategoryCreateView(StaffRequiredMixin, CreateView):
    model = MenuCategory
    form_class = MenuCategoryForm
    template_name = "menus/category_form.html"
    success_url = reverse_lazy("menus:manage")

    def form_valid(self, form):
        messages.success(self.request, "เพิ่มหมวดหมู่เมนูเรียบร้อยแล้ว")
        return super().form_valid(form)


class MenuCategoryDeleteView(StaffRequiredMixin, DeleteView):
    """ลบหมวดหมู่เมนู - เมนูที่เคยอยู่ในหมวดหมู่นี้จะไม่ถูกลบตามไปด้วย แต่จะกลายเป็น 'ไม่มีหมวดหมู่' (category=NULL)"""

    model = MenuCategory
    success_url = reverse_lazy("menus:manage")
    template_name = "menus/category_confirm_delete.html"

    def form_valid(self, form):
        name = self.object.name
        messages.success(self.request, f'ลบหมวดหมู่ "{name}" เรียบร้อยแล้ว')
        return super().form_valid(form)
