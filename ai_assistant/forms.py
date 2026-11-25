from django import forms

from .models import KnowledgeSnippet


class KnowledgeSnippetForm(forms.ModelForm):
    class Meta:
        model = KnowledgeSnippet
        fields = ["source_type", "content"]
        widgets = {
            "content": forms.Textarea(attrs={"rows": 4}),
        }
