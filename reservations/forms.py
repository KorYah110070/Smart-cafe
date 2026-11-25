from django import forms


class ReservationEditForm(forms.Form):
    """FR-32: แก้ไขการจอง (วัน/จำนวนคน - จองเป็นรายวัน ไม่มีเวลา)"""

    reservation_date = forms.DateField(
        label="วันที่ต้องการจอง", widget=forms.DateInput(attrs={"type": "date"})
    )
    party_size = forms.IntegerField(label="จำนวนคน", min_value=1, max_value=50)
