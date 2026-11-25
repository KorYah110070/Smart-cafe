from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.OrderListView.as_view(), name="my_orders"),
    path("new/<int:reservation_id>/", views.CreateOrderView.as_view(), name="create"),
    path("staff/new/<int:reservation_id>/", views.StaffCreateOrderView.as_view(), name="staff_create"),
    path("takeaway/new/", views.TakeawayCreateOrderView.as_view(), name="takeaway_create"),
    path("<int:pk>/status/", views.AdminOrderStatusUpdateView.as_view(), name="admin_status_update"),
]
