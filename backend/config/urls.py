"""Root URL configuration for the PadungGo backend."""
from django.contrib import admin
from django.urls import include, path

from transit.api.views import health

urlpatterns = [
    path("admin/", admin.site.urls),
    # Plain host health-check alias (for load balancers / platform probes).
    path("health", health, name="health-alias"),
    path("api/v1/", include("transit.api.urls")),
]
