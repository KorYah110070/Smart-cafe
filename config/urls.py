from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="tables:floor_plan", permanent=False)),
    path("accounts/", include("accounts.urls")),
    path("accounts/social/", include("allauth.urls")),
    path("tables/", include("tables.urls")),
    path("reservations/", include("reservations.urls")),
    path("menus/", include("menus.urls")),
    path("orders/", include("orders.urls")),
    path("promotions/", include("promotions.urls")),
    path("ai/", include("ai_assistant.urls")),
    path("panel/", include("dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
