from django.contrib import admin

from .models import KnowledgeSnippet


@admin.register(KnowledgeSnippet)
class KnowledgeSnippetAdmin(admin.ModelAdmin):
    list_display = ("source_type", "content", "updated_at")
    list_filter = ("source_type",)
