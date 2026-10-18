"""API views implementing the canonical docs/API_DESIGN.md contract."""
from __future__ import annotations

from datetime import date

from django.conf import settings
from rest_framework import status as http_status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from transit.models import Location, Route, RoutePattern
from transit.planner import PlanRequest, plan_journeys
from transit.planner.engine import PlannerError
from transit.planner.loader import load_network, resolve_location
from transit.planner.models import Endpoint

from .errors import error_response
from .serializers import PlanRequestSerializer

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def _planner_config() -> dict:
    cfg = getattr(settings, "PLANNER", {})
    return {
        "STOP_SEARCH_RADIUS_M": cfg.get("STOP_SEARCH_RADIUS_M", 500),
        "ALLOW_DOCUMENTED": cfg.get("ALLOW_DOCUMENTED", False),
    }


def _parse_limit(request) -> int:
    raw = request.query_params.get("limit")
    if raw is None:
        return DEFAULT_LIMIT
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_LIMIT
    return max(1, min(value, MAX_LIMIT))


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
    q = (request.query_params.get("q") or "").strip()
    area_id = request.query_params.get("area_id")
    limit = _parse_limit(request)

    qs = Location.objects.all()
    if q:
        qs = qs.filter(name__icontains=q)
    if area_id:
        qs = qs.filter(area_id=area_id)
    qs = qs.order_by("name", "id")[: limit + 1]
    rows = list(qs)
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = str(rows[-1].id)

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
    """Verified active services with directional pattern summaries."""
    area_id = request.query_params.get("area_id")
    limit = _parse_limit(request)

    qs = Route.objects.filter(active=True).prefetch_related("patterns")
    rows = list(qs.order_by("code", "id")[: limit + 1])
    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        next_cursor = str(rows[-1].id)

    data = []
    for route in rows:
        verified_patterns = [p for p in route.patterns.all() if p.status == "verified"]
        if area_id:
            # area filtering is derived from stops; omitted for list summary.
            pass
        data.append({
            "id": str(route.id),
            "code": route.code,
            "name": route.name,
            "vehicle_class": route.vehicle_class,
            "operator": route.operator or None,
            "patterns": [{
                "id": str(p.id),
                "direction": p.direction,
                "variant_key": p.variant_key,
                "signboard": p.signboard or None,
                "status": p.status,
            } for p in verified_patterns],
        })
    return Response({"results": data, "next_cursor": next_cursor})


# --- Route detail ----------------------------------------------------------


@api_view(["GET"])
def route_detail(request, route_id: str):
    """Full verified route detail. Unknown/unpublished -> 404."""
    from django.core.exceptions import ValidationError

    try:
        route = Route.objects.prefetch_related(
            "patterns__pattern_stops__stop", "patterns__evidence__source"
        ).get(id=route_id, active=True)
    except (Route.DoesNotExist, ValidationError, ValueError, TypeError):
        return error_response("not_found", "Route not found.", http=http_status.HTTP_404_NOT_FOUND)

    verified_patterns = [p for p in route.patterns.all() if p.status == "verified"]
    if not verified_patterns:
        return error_response("not_found", "Route not found.", http=http_status.HTTP_404_NOT_FOUND)

    patterns = []
    for p in verified_patterns:
        occurrences = [{
            "occurrence_id": str(ps.id),
            "stop_id": str(ps.stop_id),
            "stop_name": ps.stop.name,
            "sequence": ps.sequence,
            "distance_along_m": ps.distance_along_m,
            "can_board": ps.can_board,
            "can_alight": ps.can_alight,
            "latitude": ps.stop.latitude,
            "longitude": ps.stop.longitude,
        } for ps in sorted(p.pattern_stops.all(), key=lambda x: x.sequence)]
        evidence = [{
            "source_id": str(e.source_id),
            "status": e.status,
            "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None,
            "observed_at": e.observed_at.isoformat() if e.observed_at else None,
        } for e in p.evidence.all() if e.status == "verified"]
        patterns.append({
            "id": str(p.id),
            "direction": p.direction,
            "variant_key": p.variant_key,
            "signboard": p.signboard or None,
            "verified_at": p.verified_at.isoformat() if p.verified_at else None,
            "stops": occurrences,
            "evidence": evidence,
        })

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

    return Response(result.to_dict())


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
