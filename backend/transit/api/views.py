"""API views implementing the canonical docs/API_DESIGN.md contract."""
from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status as http_status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from transit.models import Location, NetworkDataVersion, Route, RoutePattern
from transit.planner import PlanRequest, plan_journeys
from transit.planner.engine import PlannerError
from transit.planner.loader import load_network, resolve_location
from transit.planner.journey_types import Endpoint
from transit.places.suggestions import filter_by_words
from transit.search_text import normalise_query

from .errors import error_response
from .geometry import attach_ride_geometry
from .query_params import _paginate, _parse_uuid_param
from .serializers import PlanRequestSerializer


def _planner_config() -> dict:
    cfg = getattr(settings, "PLANNER", {})
    return {
        "STOP_SEARCH_RADIUS_M": cfg.get("STOP_SEARCH_RADIUS_M", 500),
        "ALLOW_DOCUMENTED": cfg.get("ALLOW_DOCUMENTED", False),
    }

def _pattern_summary(pattern: RoutePattern) -> dict:
    return {
        "id": str(pattern.id),
        "direction": pattern.direction,
        "variant_key": pattern.variant_key,
        "signboard": pattern.signboard or None,
    }


def _pattern_detail(pattern: RoutePattern) -> dict:
    occurrences = [{
        "occurrence_id": str(occurrence.id),
        "stop_id": str(occurrence.stop_id),
        "stop_name": occurrence.stop.name,
        "sequence": occurrence.sequence,
        "distance_along_m": occurrence.distance_along_m,
        "can_board": occurrence.can_board,
        "can_alight": occurrence.can_alight,
        "latitude": occurrence.stop.latitude,
        "longitude": occurrence.stop.longitude,
    } for occurrence in sorted(pattern.pattern_stops.all(), key=lambda item: item.sequence)]
    evidence = [{
        "source_id": str(record.source_id),
        "status": record.status,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "observed_at": record.observed_at.isoformat() if record.observed_at else None,
    } for record in pattern.evidence.all() if record.status == "verified"]
    return {
        **_pattern_summary(pattern),
        "verified_at": pattern.verified_at.isoformat() if pattern.verified_at else None,
        "stops": occurrences,
        "evidence": evidence,
    }

# --- Health ----------------------------------------------------------------


@api_view(["GET"])
@throttle_classes([])
def health(request):
    """Minimal service status. No secrets or connection strings."""
    return Response({
        "status": "ok",
        "service": "padunggo-backend",
        "spatial_mode": "postgis" if getattr(settings, "GIS_ENABLED", False) else "lite",
    })


# --- Locations -------------------------------------------------------------


@api_view(["GET"])
def locations(request):
    """Curated location search. Not a promise of transit availability."""
    tokens = normalise_query(request.query_params.get("q") or "")
    area_id = _parse_uuid_param(request, "area_id")

    qs = Location.objects.select_related("area")
    # Matches word beginnings of the name, aliases and acronyms, ignoring case/accents.
    qs = filter_by_words(qs, tokens)
    if area_id:
        qs = qs.filter(area_id=area_id)
    rows, next_cursor = _paginate(request, qs, "name")

    data = [{
        "id": str(loc.id),
        "name": loc.name,
        "kind": loc.kind,
        "area": loc.area.name if loc.area_id else None,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "status": loc.status,
    } for loc in rows]
    return Response({"results": data, "next_cursor": next_cursor})


# --- Routes list -----------------------------------------------------------


@api_view(["GET"])
def routes(request):
    """Active services with their verified directional pattern summaries.

    `area_id` keeps only routes that stop somewhere in that area (an exact area
    match on the route's stops; child areas are not included).
    """
    area_id = _parse_uuid_param(request, "area_id")

    qs = Route.objects.filter(active=True).prefetch_related("patterns")
    if area_id:
        qs = qs.filter(patterns__pattern_stops__stop__area_id=area_id).distinct()
    rows, next_cursor = _paginate(request, qs, "code")

    data = []
    for route in rows:
        verified_patterns = [p for p in route.patterns.all() if p.status == "verified"]
        data.append({
            "id": str(route.id),
            "code": route.code,
            "name": route.name,
            "vehicle_class": route.vehicle_class,
            "operator": route.operator or None,
            "patterns": [{
                **_pattern_summary(p),
                "status": p.status,
            } for p in verified_patterns],
        })
    return Response({"results": data, "next_cursor": next_cursor})


# --- Route detail ----------------------------------------------------------


@api_view(["GET"])
def route_detail(request, route_id: str):
    """Full verified route detail. Unknown/unpublished -> 404."""
    try:
        route = Route.objects.prefetch_related(
            "patterns__pattern_stops__stop", "patterns__evidence__source"
        ).get(id=route_id, active=True)
    except (Route.DoesNotExist, DjangoValidationError, ValueError, TypeError):
        return error_response("not_found", "Route not found.", http=http_status.HTTP_404_NOT_FOUND)

    verified_patterns = [p for p in route.patterns.all() if p.status == "verified"]
    if not verified_patterns:
        return error_response("not_found", "Route not found.", http=http_status.HTTP_404_NOT_FOUND)

    patterns = [_pattern_detail(pattern) for pattern in verified_patterns]

    return Response({
        "id": str(route.id),
        "code": route.code,
        "name": route.name,
        "vehicle_class": route.vehicle_class,
        "operator": route.operator or None,
        "patterns": patterns,
    })


# --- Journey plan ----------------------------------------------------------


@api_view(["POST"])
@throttle_classes([ScopedRateThrottle])
def plan_journey(request):
    """Plan journeys (and, by swapping endpoints in a second call, returns)."""
    serializer = PlanRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        origin = _resolve_endpoint(data["origin"])
        destination = _resolve_endpoint(data["destination"])
    except _UnresolvableLocation as exc:
        return error_response(
            "invalid_request", str(exc), http=http_status.HTTP_400_BAD_REQUEST,
            fields={"location_id": [str(exc)]},
        )

    plan_req = PlanRequest(
        origin=origin, destination=destination,
        max_transfers=data["max_transfers"], limit=data["limit"],
        sort_by=data["sort_by"], query_date=date.today(),
    )
    config = _planner_config()
    network = load_network(allow_documented=config["ALLOW_DOCUMENTED"])
    try:
        result = plan_journeys(network, plan_req, config=config)
    except PlannerError as exc:
        return error_response("invalid_request", str(exc), http=http_status.HTTP_400_BAD_REQUEST)

    payload = result.to_dict()
    updated_at = (
        NetworkDataVersion.objects
        .filter(pk=NetworkDataVersion.SINGLETON_ID)
        .values_list("updated_at", flat=True)
        .first()
    )
    payload["data_updated_on"] = (
        updated_at.astimezone(ZoneInfo("Asia/Manila")).date().isoformat()
        if updated_at is not None
        else None
    )
    attach_ride_geometry(payload["journey_options"])
    return Response(payload)

plan_journey.throttle_scope = "plan"


class _UnresolvableLocation(Exception):
    pass


def _resolve_endpoint(ep_data: dict) -> Endpoint:
    if "location_id" in ep_data:
        loc = resolve_location(ep_data["location_id"])
        if loc is None:
            raise _UnresolvableLocation(f"Unknown location_id: {ep_data['location_id']}")
        return Endpoint(latitude=loc.latitude, longitude=loc.longitude,
                        location_id=str(loc.id), name=loc.name)
    return Endpoint(latitude=ep_data["latitude"], longitude=ep_data["longitude"])
