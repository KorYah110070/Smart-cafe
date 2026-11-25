from django.urls import path

from . import views

app_name = "promotions"

urlpatterns = [
    path("", views.PromotionListView.as_view(), name="promotion_list"),
    path("manage/", views.PromotionManageListView.as_view(), name="manage"),
    path("manage/add/", views.PromotionCreateView.as_view(), name="promotion_add"),
    path("manage/<int:pk>/edit/", views.PromotionUpdateView.as_view(), name="promotion_edit"),
    path("manage/<int:pk>/delete/", views.PromotionDeleteView.as_view(), name="promotion_delete"),
]
