"""Orchestrate deterministic journey planning without Django dependencies."""
from __future__ import annotations

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
from .search import MAX_TRANSFER_CANDIDATES, build_search_context, enumerate_options
from .validation import PlannerError, SORTS, validate_request

_SAME_POINT_EPS_M = 25.0


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
        return empty_result(req, REASON_INSUFFICIENT)

    options = deduplicate_options(enumerate_options(context, req.max_transfers))
    if not options:
        return empty_result(req, REASON_NO_JOURNEY)

    return journey_result(
        options, req, allow_documented=allow_documented,
        response_prefix=response_prefix,
    )
