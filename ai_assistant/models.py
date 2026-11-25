from django.db import models


class KnowledgeSnippet(models.Model):
    """
    ข้อมูลความรู้สำหรับ RAG Knowledge Base (FR-27)
    เก็บข้อมูลเมนู/โปรโมชั่น/โต๊ะ เป็นข้อความสั้น ๆ ที่พร้อมส่งให้ LLM ใช้ตอบคำถาม
    ขั้นต่อไป (นอกเหนือ scope โค้ดชุดนี้): เชื่อมต่อ LLM API จริง (เช่น OpenAI/Gemini)
    และทำ vector search แทนการค้นหาแบบ keyword ธรรมดา
    """

    class SourceType(models.TextChoices):
        TABLE = "table", "ข้อมูลโต๊ะ/ผังร้าน"
        MENU = "menu", "ข้อมูลเมนู"
        PROMOTION = "promotion", "ข้อมูลโปรโมชั่น"

    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    content = models.TextField(help_text="ข้อความสรุปสำหรับส่งเป็น context ให้ LLM")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_source_type_display()}] {self.content[:50]}"
