from django.db import models


class MenuCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="หมวดหมู่")

    class Meta:
        verbose_name_plural = "Menu categories"

    def __str__(self):
        return self.name


class MenuItem(models.Model):
    """FR-10, FR-25: เมนูอาหารและเครื่องดื่ม"""

    category = models.ForeignKey(
        MenuCategory, on_delete=models.SET_NULL, null=True, related_name="items"
    )
    name = models.CharField(max_length=150, verbose_name="ชื่อเมนู")
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to="menu_items/", blank=True, null=True)
    is_available = models.BooleanField(default=True)
    is_recommended = models.BooleanField(default=False, verbose_name="เมนูแนะนำ")

    def __str__(self):
        return f"{self.name} ({self.price} บาท)"
