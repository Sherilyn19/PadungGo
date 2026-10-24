"""Orchestrate deterministic journey planning without Django dependencies."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from typing import Optional

from .eligibility import allowed_statuses
from .geo import haversine_m
from .journey_types import Network, PlanRequest, PlanResult
from .ranking import deduplicate_options
from .responses import (
    LIMITED,
    OUTSIDE,
    REASON_INSUFFICIENT,
    REASON_NO_JOURNEY,
    REASON_OUTSIDE,
    REASON_SAME_LOCATION,
    WITHIN,
    empty_result,
    journey_result,
)
from .search import build_search_context, enumerate_options, nearest_stop_distance_m
from .validation import PlannerError, SORTS, validate_request

_SAME_POINT_EPS_M = 25.0


def _coverage(network, req, context, statuses, radius_m, *, check_reverse: bool) -> dict:
    """Why no trip was found: which end has no stop within the radius, and how far the
    nearest one is. For a one-way gap, also whether the opposite direction has trips."""
    origin_has = bool(context.origin_stops)
    destination_has = bool(context.destination_stops)
    return {
        "search_radius_m": int(radius_m),
        "origin_has_stop": origin_has,
        "destination_has_stop": destination_has,
        "nearest_origin_stop_m": nearest_stop_distance_m(
            network, req.origin, boarding=True, allowed_statuses=statuses),
        "nearest_destination_stop_m": nearest_stop_distance_m(
            network, req.destination, boarding=False, allowed_statuses=statuses),
        "reverse_has_trips": _reverse_has_trips(network, req, radius_m, statuses) if check_reverse else None,
    }


def _reverse_has_trips(network, req, radius_m, statuses) -> bool:
    """True if the same places can be travelled the other way (routes may run one way)."""
    swapped = replace(req, origin=req.destination, destination=req.origin)
    context = build_search_context(
        network, swapped, radius_m=radius_m, statuses=statuses,
        passenger_category="regular", on=req.query_date or date.today(),
    )
    if not context.origin_stops or not context.destination_stops:
        return False
    return bool(enumerate_options(context, req.max_transfers))


def plan_journeys(network: Network, req: PlanRequest, *, config: Optional[dict] = None,
                  response_prefix: str = "opt") -> PlanResult:
    """Plan one request. Call again with swapped endpoints for a return trip."""
    validate_request(req)
    config = config or {}
    radius_m = float(config.get("STOP_SEARCH_RADIUS_M", 500))
    allow_documented = bool(config.get("ALLOW_DOCUMENTED", False))
    passenger_category = config.get("passenger_category", "regular")
    on = req.query_date or date.today()
    statuses = allowed_statuses(allow_documented)

    if haversine_m(
        req.origin.latitude, req.origin.longitude,
        req.destination.latitude, req.destination.longitude,
    ) <= _SAME_POINT_EPS_M:
        return empty_result(req, REASON_SAME_LOCATION)

    context = build_search_context(
        network, req, radius_m=radius_m, statuses=statuses,
        passenger_category=passenger_category, on=on,
    )
    if not context.origin_stops or not context.destination_stops:
        coverage = _coverage(network, req, context, statuses, radius_m, check_reverse=False)
        return empty_result(req, REASON_INSUFFICIENT, coverage)

    options = deduplicate_options(enumerate_options(context, req.max_transfers))
    if not options:
        coverage = _coverage(network, req, context, statuses, radius_m, check_reverse=True)
        return empty_result(req, REASON_NO_JOURNEY, coverage)

    return journey_result(
        options, req, allow_documented=allow_documented,
        response_prefix=response_prefix,
    )
