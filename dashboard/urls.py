from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("stats/", views.CustomerStatsView.as_view(), name="stats"),
    path("sales/", views.SalesStatsView.as_view(), name="sales_stats"),
    path("sales/report/", views.SalesReportDownloadView.as_view(), name="sales_report_download"),
    path("settings/", views.SiteSettingsView.as_view(), name="settings"),
]
