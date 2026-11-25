from django.urls import path

from . import views

app_name = "menus"

urlpatterns = [
    path("", views.MenuListView.as_view(), name="menu_list"),
    path("manage/", views.MenuManageListView.as_view(), name="manage"),
    path("manage/add/", views.MenuItemCreateView.as_view(), name="item_add"),
    path("manage/<int:pk>/edit/", views.MenuItemUpdateView.as_view(), name="item_edit"),
    path("manage/<int:pk>/delete/", views.MenuItemDeleteView.as_view(), name="item_delete"),
    path("manage/category/add/", views.MenuCategoryCreateView.as_view(), name="category_add"),
    path(
        "manage/category/<int:pk>/delete/",
        views.MenuCategoryDeleteView.as_view(),
        name="category_delete",
    ),
]
