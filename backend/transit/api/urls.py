"""API v1 URL routes (canonical paths, no trailing slash)."""
from django.urls import path

from . import explain_views, place_views, views

app_name = "api"

urlpatterns = [
    path("health", views.health, name="health"),
    path("locations", views.locations, name="locations"),
    path("places/suggestions", place_views.suggestions, name="place-suggestions"),
    path("places/address", place_views.address, name="place-address"),
    path("routes", views.routes, name="routes"),
    path("routes/<str:route_id>", views.route_detail, name="route-detail"),
    path("journeys/plan", views.plan_journey, name="journeys-plan"),
    path("journeys/explain", explain_views.explain_journey, name="journeys-explain"),
]
