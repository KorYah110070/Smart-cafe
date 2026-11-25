from django import forms

from .models import Promotion


class PromotionForm(forms.ModelForm):
    class Meta:
        model = Promotion
        fields = ["title", "description", "discount_percent", "start_date", "end_date", "is_active", "image"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }
