import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from accounts.mixins import StaffRequiredMixin

from .forms import KnowledgeSnippetForm
from .models import KnowledgeSnippet
from .services import generate_answer


class ChatbotView(View):
    """FR-15: ผู้ใช้ (รวมผู้เยี่ยมชม) สามารถใช้งาน AI Chatbot สอบถามข้อมูลเกี่ยวกับโต๊ะ เมนู โปรโมชั่นได้ (หน้าเต็ม)"""

    template_name = "ai_assistant/chat.html"

    def get(self, request):
        return render(request, self.template_name, {"answer": None})

    def post(self, request):
        question = request.POST.get("question", "").strip()
        answer = generate_answer(question) if question else None
        return render(
            request, self.template_name, {"answer": answer, "question": question}
        )


class ChatbotAPIView(View):
    """
    FR-15: endpoint แบบ JSON สำหรับกล่องแชทป๊อปอัพลอยในหน้าแดชบอร์ด (tables/floor_plan.html)
    ใช้ fetch() จาก JavaScript แทนการเปลี่ยนหน้าไปหน้า /ai/ เต็มหน้า
    """

    def post(self, request):
        try:
            data = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            data = {}
        question = (data.get("question") or "").strip()
        if not question:
            return JsonResponse({"error": "กรุณาพิมพ์คำถาม"}, status=400)
        answer = generate_answer(question)
        return JsonResponse({"answer": answer})


class KnowledgeManageListView(StaffRequiredMixin, ListView):
    """
    FR-27: หน้า 'จัดการ AI Chatbot' ของแอดมิน/พนักงาน
    จัดการข้อมูลความรู้ (Knowledge Base) ที่ใช้เป็น context ให้ RAG chatbot ตอบคำถามลูกค้า
    """

    model = KnowledgeSnippet
    template_name = "ai_assistant/manage_list.html"
    context_object_name = "snippets"
    queryset = KnowledgeSnippet.objects.all().order_by("source_type", "-updated_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["source_type_choices"] = KnowledgeSnippet.SourceType.choices
        context["test_question"] = self.request.GET.get("q", "")
        if context["test_question"]:
            context["test_answer"] = generate_answer(context["test_question"])
        return context


class KnowledgeCreateView(StaffRequiredMixin, CreateView):
    model = KnowledgeSnippet
    form_class = KnowledgeSnippetForm
    template_name = "ai_assistant/knowledge_form.html"
    success_url = reverse_lazy("ai_assistant:manage")

    def form_valid(self, form):
        messages.success(self.request, "เพิ่มข้อมูลความรู้ใหม่เรียบร้อยแล้ว")
        return super().form_valid(form)


class KnowledgeUpdateView(StaffRequiredMixin, UpdateView):
    model = KnowledgeSnippet
    form_class = KnowledgeSnippetForm
    template_name = "ai_assistant/knowledge_form.html"
    success_url = reverse_lazy("ai_assistant:manage")

    def form_valid(self, form):
        messages.success(self.request, "แก้ไขข้อมูลความรู้เรียบร้อยแล้ว")
        return super().form_valid(form)


class KnowledgeDeleteView(StaffRequiredMixin, DeleteView):
    model = KnowledgeSnippet
    success_url = reverse_lazy("ai_assistant:manage")
    template_name = "ai_assistant/knowledge_confirm_delete.html"
