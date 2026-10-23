"""Address labels and place suggestions.

Both endpoints are throttled per client so ordinary use cannot exhaust the
provider's daily quota. Provider problems return 200 with a status, because
the app still works without an address or extra suggestions.
"""
from __future__ import annotations

from rest_framework import serializers
from rest_framework import status as http_status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from transit.places.geoapify import reverse_address
from transit.places.suggestions import place_suggestions

from .errors import error_response

MAX_QUERY_LENGTH = 100


class PlacesRateThrottle(AnonRateThrottle):
    """Per-client limit for endpoints that may call the paid-quota provider."""

    scope = "places"


class PointSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


@api_view(["GET"])
@throttle_classes([AnonRateThrottle, PlacesRateThrottle])
def suggestions(request):
    query = (request.query_params.get("q") or "").strip()[:MAX_QUERY_LENGTH]
    return Response(place_suggestions(query))


# POST keeps coordinates out of URLs, so server access logs never record them.
@api_view(["POST"])
@throttle_classes([AnonRateThrottle, PlacesRateThrottle])
def address(request):
    point = PointSerializer(data=request.data)
    if not point.is_valid():
        return error_response("invalid_request", "Provide a valid latitude and longitude.",
                              http=http_status.HTTP_400_BAD_REQUEST, fields=point.errors)
    data = point.validated_data
    return Response(reverse_address(data["latitude"], data["longitude"]))
