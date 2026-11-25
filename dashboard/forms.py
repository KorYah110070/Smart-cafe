from django import forms
from django.contrib.auth.forms import PasswordChangeForm

from accounts.models import User

from .models import SiteSettings


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "cafe_name",
            "description",
            "address",
            "phone_number",
            "contact_email",
            "opening_time",
            "closing_time",
            "logo",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }
        labels = {
            "cafe_name": "ชื่อร้าน",
            "description": "คำอธิบายร้าน",
            "address": "ที่อยู่ร้าน",
            "phone_number": "เบอร์โทรศัพท์ร้าน",
            "contact_email": "อีเมลติดต่อร้าน",
            "opening_time": "เวลาเปิด",
            "closing_time": "เวลาปิด",
            "logo": "โลโก้ร้าน",
        }


class AdminProfileForm(forms.ModelForm):
    """ฟอร์มแก้ไข 'ข้อมูลผู้ดูแลระบบ' - ชื่อผู้ใช้/อีเมล/เบอร์โทรของผู้ดูแลระบบที่ล็อกอินอยู่"""

    class Meta:
        model = User
        fields = ["username", "email", "phone_number"]
        labels = {
            "username": "ชื่อผู้ใช้",
            "email": "ที่อยู่อีเมล",
            "phone_number": "เบอร์โทรศัพท์",
        }


class AdminPasswordChangeForm(PasswordChangeForm):
    pass
