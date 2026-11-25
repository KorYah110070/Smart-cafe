from django.urls import path

from . import views

app_name = "ai_assistant"

urlpatterns = [
    path("", views.ChatbotView.as_view(), name="chat"),
    path("api/ask/", views.ChatbotAPIView.as_view(), name="chat_api"),
    path("manage/", views.KnowledgeManageListView.as_view(), name="manage"),
    path("manage/add/", views.KnowledgeCreateView.as_view(), name="knowledge_add"),
    path("manage/<int:pk>/edit/", views.KnowledgeUpdateView.as_view(), name="knowledge_edit"),
    path("manage/<int:pk>/delete/", views.KnowledgeDeleteView.as_view(), name="knowledge_delete"),
]
