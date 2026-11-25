from django import forms

from .models import Table, TableGroup


class TableForm(forms.ModelForm):
    """
    ฟอร์มแก้ไขโต๊ะ (ไม่รวม pos_x/pos_y เพราะตำแหน่งบนผังจะถูกกำหนดผ่านฟีเจอร์
    'ลากวาง' บนหน้า Dashboard แทน - ดู TablePositionUpdateView)
    """

    class Meta:
        model = Table
        fields = ["table_number", "zone", "capacity", "shape", "status"]


class TableGroupForm(forms.ModelForm):
    tables = forms.ModelMultipleChoiceField(
        queryset=Table.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label="โต๊ะที่รวมกันได้",
    )

    class Meta:
        model = TableGroup
        fields = ["group_name", "tables"]
