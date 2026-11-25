from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class CafeAuthenticationForm(AuthenticationForm):
    """FR-02: เข้าสู่ระบบ (ปรับ placeholder ให้เข้ากับหน้า Login ที่ออกแบบไว้)"""

    username = forms.CharField(
        widget=forms.TextInput(attrs={"placeholder": "Username", "autofocus": True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "Password"})
    )


class RegisterForm(UserCreationForm):
    """FR-01: ผู้ใช้สามารถสมัครสมาชิกได้"""

    email = forms.EmailField(
        required=True,
        label="อีเมล",
        widget=forms.EmailInput(attrs={"placeholder": "อีเมล"}),
    )
    phone_number = forms.CharField(
        required=False,
        label="เบอร์โทรศัพท์",
        widget=forms.TextInput(attrs={"placeholder": "เบอร์โทรศัพท์ (ไม่บังคับ)"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "phone_number", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "ชื่อผู้ใช้", "autofocus": True})
        self.fields["password1"].widget.attrs.update({"placeholder": "รหัสผ่าน"})
        self.fields["password2"].widget.attrs.update({"placeholder": "ยืนยันรหัสผ่าน"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.phone_number = self.cleaned_data.get("phone_number", "")
        user.role = User.Role.CUSTOMER
        if commit:
            user.save()
        return user


class StaffCreateForm(UserCreationForm):
    """ให้แอดมิน/พนักงานเพิ่มบัญชีพนักงานเสิร์ฟ (หรือแอดมินคนใหม่) ได้โดยตรงจากหน้า 'จัดการสมาชิก'
    โดยไม่ต้องให้พนักงานไปสมัครสมาชิกเองแล้วค่อยมาเปลี่ยนบทบาทภายหลัง"""

    email = forms.EmailField(
        required=True,
        label="อีเมล",
        widget=forms.EmailInput(attrs={"placeholder": "อีเมล"}),
    )
    role = forms.ChoiceField(
        label="บทบาท",
        choices=[(User.Role.STAFF, "พนักงาน"), (User.Role.ADMIN, "แอดมิน")],
        initial=User.Role.STAFF,
    )

    class Meta:
        model = User
        fields = ["username", "email", "role", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"placeholder": "ชื่อผู้ใช้", "autofocus": True})
        self.fields["password1"].widget.attrs.update({"placeholder": "รหัสผ่าน"})
        self.fields["password2"].widget.attrs.update({"placeholder": "ยืนยันรหัสผ่าน"})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.role = self.cleaned_data["role"]
        if commit:
            user.save()
        return user
