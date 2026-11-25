from django.urls import path

from . import views

app_name = "tables"

urlpatterns = [
    path("", views.FloorPlanView.as_view(), name="floor_plan"),
    # --- ฝั่งจัดการ (แอดมิน/พนักงาน) ---
    path("manage/", views.TableManageListView.as_view(), name="manage"),
    path("manage/add/", views.TableCreateView.as_view(), name="table_add"),
    path("manage/<int:pk>/edit/", views.TableUpdateView.as_view(), name="table_edit"),
    path("manage/<int:pk>/delete/", views.TableDeleteView.as_view(), name="table_delete"),
    path("manage/<int:pk>/status/", views.TableStatusUpdateView.as_view(), name="table_status_update"),
    path("manage/<int:pk>/position/", views.TablePositionUpdateView.as_view(), name="table_position_update"),
    path("manage/groups/", views.TableGroupListView.as_view(), name="group_list"),
    path("manage/groups/add/", views.TableGroupCreateView.as_view(), name="group_add"),
    path("manage/groups/<int:pk>/delete/", views.TableGroupDeleteView.as_view(), name="group_delete"),
    # --- สิ่งกีดขวาง/จุดสำคัญบนผังร้าน (บาร์, ทางเข้า-ออก, เวที, บาร์น้ำ, ทางหนีไฟ, บันได, แคชเชียร์) ---
    path("landmarks/add/", views.FloorLandmarkCreateView.as_view(), name="landmark_add"),
    path(
        "landmarks/<int:pk>/geometry/",
        views.FloorLandmarkGeometryUpdateView.as_view(),
        name="landmark_geometry_update",
    ),
    path("landmarks/<int:pk>/delete/", views.FloorLandmarkDeleteView.as_view(), name="landmark_delete"),
]
