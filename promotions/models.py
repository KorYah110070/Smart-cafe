from django.db import models


class Promotion(models.Model):
    """FR-26: การจัดการโปรโมชั่น"""

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    discount_percent = models.PositiveIntegerField(default=0)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    image = models.ImageField(upload_to="promotions/", blank=True, null=True, verbose_name="รูปภาพโปรโมชั่น")

    def __str__(self):
        return self.title
