"""API views. Health implemented now; data/plan endpoints added in Phase C."""
from __future__ import annotations

from django.conf import settings
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response


@api_view(["GET"])
@throttle_classes([])
def health(request):
    """Minimal service status. No secrets or connection strings."""
    return Response(
        {
            "status": "ok",
            "service": "padunggo-backend",
            "spatial_mode": "postgis" if getattr(settings, "GIS_ENABLED", False) else "lite",
        }
    )
