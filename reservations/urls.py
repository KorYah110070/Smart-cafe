from django.urls import path

from . import views

app_name = "reservations"

urlpatterns = [
    path("", views.MyReservationListView.as_view(), name="my_reservations"),
    path("new/", views.ReservationDateStepView.as_view(), name="create"),
    path("new/<str:date_str>/", views.ReservationFloorPlanBookingView.as_view(), name="create_floorplan"),
    path("<int:pk>/edit/", views.EditReservationView.as_view(), name="edit"),
    path("<int:pk>/cancel/", views.CancelReservationView.as_view(), name="cancel"),
    path("manage/", views.AdminReservationListView.as_view(), name="admin_list"),
    path("manage/<int:pk>/status/", views.AdminReservationStatusUpdateView.as_view(), name="admin_status_update"),
    path("walkin/new/", views.WalkinSeatView.as_view(), name="walkin_seat"),
]
