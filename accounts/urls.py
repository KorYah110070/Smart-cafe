from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.CafeLoginView.as_view(), name="login"),
    path("logout/", views.CafeLogoutView.as_view(), name="logout"),
    path("members/", views.MemberListView.as_view(), name="member_list"),
    path("members/add/", views.MemberCreateView.as_view(), name="member_add"),
    path("members/<int:pk>/toggle/", views.MemberToggleActiveView.as_view(), name="member_toggle"),
    path("members/<int:pk>/role/", views.MemberRoleUpdateView.as_view(), name="member_role_update"),
]
