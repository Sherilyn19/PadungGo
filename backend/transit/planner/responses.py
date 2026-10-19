"""Planner coverage responses and public journey output."""
from __future__ import annotations

from .journey_types import PlanRequest, PlanResult
from .ranking import apply_labels, rank_options

WITHIN = "within_verified_network"
LIMITED = "limited_verified_coverage"
OUTSIDE = "outside_intended_area"

REASON_SAME_LOCATION = "same_location"
REASON_INSUFFICIENT = "insufficient_verified_data"
REASON_NO_JOURNEY = "no_journey_within_mvp_limits"
REASON_OUTSIDE = "outside_intended_area"

_EMPTY_WARNINGS = {
    REASON_SAME_LOCATION: "Origin and destination are effectively the same location.",
    REASON_INSUFFICIENT: "No eligible verified boarding/alighting stop near one or both endpoints.",
    REASON_NO_JOURNEY: "No verified journey is available in the current dataset within MVP limits.",
}


def empty_result(req: PlanRequest, reason: str) -> PlanResult:
    return PlanResult(
        request_coverage_status=LIMITED,
        reason=reason,
        journey_options=[],
        ranking={"requested": req.sort_by, "applied": req.sort_by, "warning": None},
        warnings=[_EMPTY_WARNINGS[reason]],
    )


def _strip_internal(options: list[dict], response_prefix: str) -> list[dict]:
    public = []
    for index, option in enumerate(options):
        option = dict(option)
        option.pop("_dedup_key", None)
        option.pop("_walk_known_m", None)
        option.pop("_ride_m", None)
        option["id"] = f"{response_prefix}-{index+1}"
        public.append(option)
    return public


def _attach_walk_points(options: list[dict], req: PlanRequest) -> None:
    """Give access and egress walks endpoints from the request and rides."""
    origin = {"latitude": req.origin.latitude, "longitude": req.origin.longitude}
    destination = {
        "latitude": req.destination.latitude,
        "longitude": req.destination.longitude,
    }
    for option in options:
        segments = option["segments"]
        for index, segment in enumerate(segments):
            if segment["mode"] != "walk":
                continue
            segment["start"] = segments[index - 1]["end"] if index > 0 else origin
            segment["end"] = (
                segments[index + 1]["start"]
                if index + 1 < len(segments)
                else destination
            )


def journey_result(
    options: list[dict], req: PlanRequest, *,
    allow_documented: bool, response_prefix: str,
) -> PlanResult:
    options, ranking = rank_options(options, req.sort_by)
    options = options[: req.limit]
    # Labels compare the returned options, after the requested limit.
    apply_labels(options)
    public = _strip_internal(options, response_prefix)
    _attach_walk_points(public, req)

    warnings = []
    if allow_documented:
        warnings.append(
            "Results may include historic/documented data that is NOT field-verified for current service."
        )
    return PlanResult(
        request_coverage_status=WITHIN if not allow_documented else LIMITED,
        reason=None,
        journey_options=public,
        ranking=ranking,
        warnings=warnings,
    )