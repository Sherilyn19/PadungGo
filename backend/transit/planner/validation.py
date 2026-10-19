"""Validation for resolved planner requests."""
from __future__ import annotations

from .journey_types import Endpoint, PlanRequest

SORTS = ("fewest_transfers", "cheapest", "fastest", "least_walking")


class PlannerError(ValueError):
    """Raised for invalid planner inputs (maps to HTTP 400 at the API layer)."""


def _validate_endpoint(endpoint: Endpoint, label: str) -> None:
    coordinates = (
        ("latitude", endpoint.latitude, -90, 90),
        ("longitude", endpoint.longitude, -180, 180),
    )
    for name, value, lower, upper in coordinates:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise PlannerError(f"{label} {name} must be a finite number.")
        if value != value or value in (float("inf"), float("-inf")):
            raise PlannerError(f"{label} {name} must be finite.")
        if not (lower <= value <= upper):
            raise PlannerError(f"{label} {name} out of range [{lower}, {upper}].")


def validate_request(req: PlanRequest) -> None:
    _validate_endpoint(req.origin, "origin")
    _validate_endpoint(req.destination, "destination")
    if req.max_transfers not in (0, 1):
        raise PlannerError("max_transfers must be 0 or 1.")
    if not (1 <= req.limit <= 5):
        raise PlannerError("limit must be between 1 and 5.")
    if req.sort_by not in SORTS:
        raise PlannerError(f"sort_by must be one of {SORTS}.")
