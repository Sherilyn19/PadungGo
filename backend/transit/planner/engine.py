"""
Deterministic journey planner engine (pure Python).

Implements docs/ROUTING_ALGORITHM.md: validation, eligible-stop lookup, direct
and one-transfer enumeration with strict directionality, data-driven fares,
honest unknown propagation, deduplication and ranking. Return trips are planned
by calling plan_journeys again with origin/destination swapped (no reversal).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .fares import compute_leg_fare_centavos, resolve_fare_rule
from .geo import haversine_m
from .models import (
    Endpoint,
    Network,
    PatternData,
    PatternStopData,
    PlanRequest,
    PlanResult,
    RouteData,
)

# Coverage statuses / reasons (per docs/API_DESIGN.md).
WITHIN = "within_verified_network"
LIMITED = "limited_verified_coverage"
OUTSIDE = "outside_intended_area"

REASON_SAME_LOCATION = "same_location"
REASON_INSUFFICIENT = "insufficient_verified_data"
REASON_NO_JOURNEY = "no_journey_within_mvp_limits"
REASON_OUTSIDE = "outside_intended_area"

SORTS = ("fewest_transfers", "cheapest", "fastest", "least_walking")

_SAME_POINT_EPS_M = 25.0  # endpoints closer than this are treated as same location


class PlannerError(ValueError):
    """Raised for invalid planner inputs (maps to HTTP 400 at the API layer)."""


# --- Validation ------------------------------------------------------------


def _validate_endpoint(ep: Endpoint, label: str) -> None:
    lat, lon = ep.latitude, ep.longitude
    for name, val, lo, hi in (("latitude", lat, -90, 90), ("longitude", lon, -180, 180)):
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            raise PlannerError(f"{label} {name} must be a finite number.")
        if val != val or val in (float("inf"), float("-inf")):  # NaN/inf
            raise PlannerError(f"{label} {name} must be finite.")
        if not (lo <= val <= hi):
            raise PlannerError(f"{label} {name} out of range [{lo}, {hi}].")


def _validate_request(req: PlanRequest) -> None:
    _validate_endpoint(req.origin, "origin")
    _validate_endpoint(req.destination, "destination")
    if req.max_transfers not in (0, 1):
        raise PlannerError("max_transfers must be 0 or 1.")
    if not (1 <= req.limit <= 5):
        raise PlannerError("limit must be between 1 and 5.")
    if req.sort_by not in SORTS:
        raise PlannerError(f"sort_by must be one of {SORTS}.")


# --- Eligible stop lookup --------------------------------------------------


@dataclass(frozen=True)
class StopCandidate:
    stop_id: str
    straight_line_m: float


def _eligible_stops(network: Network, ep: Endpoint, *, radius_m: float, boarding: bool,
                    allowed_statuses: frozenset[str]) -> list[StopCandidate]:
    """Candidate stops within straight-line radius. Straight-line is a filter only."""
    out: list[StopCandidate] = []
    for stop in network.stops.values():
        if stop.status not in allowed_statuses:
            continue
        if boarding and not stop.can_board:
            continue
        if not boarding and not stop.can_alight:
            continue
        d = haversine_m(ep.latitude, ep.longitude, stop.latitude, stop.longitude)
        if d <= radius_m:
            out.append(StopCandidate(stop.id, d))
    out.sort(key=lambda c: (c.straight_line_m, c.stop_id))
    return out


# --- Pattern occurrence helpers --------------------------------------------


def _board_occurrences(pattern: PatternData, stop_id: str) -> list[PatternStopData]:
    return [o for o in pattern.stops if o.stop_id == stop_id and o.can_board]


def _alight_occurrences(pattern: PatternData, stop_id: str) -> list[PatternStopData]:
    return [o for o in pattern.stops if o.stop_id == stop_id and o.can_alight]


def _segment_metrics(pattern: PatternData, board: PatternStopData, alight: PatternStopData):
    """Sum distance (always available via distance_along_m) and riding seconds.

    Riding seconds is None (unknown) if ANY traversed segment lacks it.
    """
    distance_m = max(0, alight.distance_along_m - board.distance_along_m)
    # Build sequence->occurrence id map to walk consecutive segments.
    occ_by_seq = {o.sequence: o for o in pattern.stops}
    seqs = sorted(occ_by_seq)
    riding = 0
    riding_known = True
    seg_by_pair = {(s.from_occurrence_id, s.to_occurrence_id): s for s in pattern.segments}
    between = [s for s in seqs if board.sequence <= s <= alight.sequence]
    for a, b in zip(between, between[1:]):
        seg = seg_by_pair.get((occ_by_seq[a].id, occ_by_seq[b].id))
        if seg is None or seg.riding_seconds is None:
            riding_known = False
        else:
            riding += seg.riding_seconds
    return distance_m, (riding if riding_known else None)


# --- Journey assembly ------------------------------------------------------


def _ride_segment(network: Network, pattern: PatternData, route: RouteData,
                  board: PatternStopData, alight: PatternStopData, *,
                  passenger_category: str, on: date) -> dict:
    distance_m, riding_seconds = _segment_metrics(pattern, board, alight)
    board_stop = network.stops[board.stop_id]
    alight_stop = network.stops[alight.stop_id]

    rule = resolve_fare_rule(
        network, route=route, pattern_id=pattern.id,
        passenger_category=passenger_category, on=on,
    )
    amount = compute_leg_fare_centavos(rule, distance_m) if rule else None
    source_ids = sorted(set(pattern.evidence_source_ids))

    return {
        "mode": "ride",
        "route_id": route.id,
        "route_pattern_id": pattern.id,
        "direction": pattern.direction,
        "vehicle_class": route.vehicle_class,
        "operator": route.operator,
        "route_code": route.code,
        "route_name": route.name,
        "signboard": pattern.signboard,
        "verification_status": pattern.status,
        "board_occurrence_id": board.id,
        "alight_occurrence_id": alight.id,
        "board_stop_name": board_stop.name,
        "alight_stop_name": alight_stop.name,
        "instruction": (
            f"Board {route.code} ({pattern.direction}) at {board_stop.name}; "
            f"alight at {alight_stop.name}."
        ),
        "distance_m": distance_m,
        "duration_seconds": riding_seconds,
        "estimate_basis": "sourced_observation" if riding_seconds is not None else None,
        "waiting_seconds": None,  # unknown unless frequency evidence exists
        "fare": {
            "amount_centavos": amount,
            "rule_id": rule.id if rule else None,
            "passenger_category": passenger_category,
            "source_ids": list(rule.source_ids) if rule else [],
            "effective_date": rule.valid_from.isoformat() if rule else None,
            "assumptions": None if rule else "No verified fare rule for this leg.",
        },
        "source_ids": source_ids,
    }


def _walk_segment(from_name: str, to_name: str, straight_m: float) -> dict:
    """Access/egress/transfer walk. Straight-line only => distance/time unknown."""
    return {
        "mode": "walk",
        "instruction": f"Walk from {from_name} to {to_name} (approximate; not a verified route).",
        "distance_m": None,
        "duration_seconds": None,
        "estimate_basis": "straight_line_approx",
        "straight_line_m": round(straight_m, 1),
        "source_ids": [],
    }


def _assemble_option(network: Network, segments: list[dict], transfers: int) -> dict:
    ride_segs = [s for s in segments if s["mode"] == "ride"]

    # Fare aggregation: total only when ALL rides have a known amount.
    per_leg = []
    known_subtotal = 0
    all_known = True
    for s in ride_segs:
        amt = s["fare"]["amount_centavos"]
        per_leg.append({
            "segment_route_pattern_id": s["route_pattern_id"],
            "amount_centavos": amt,
            "rule_id": s["fare"]["rule_id"],
            "passenger_category": s["fare"]["passenger_category"],
            "source_ids": s["fare"]["source_ids"],
            "effective_date": s["fare"]["effective_date"],
            "assumptions": s["fare"]["assumptions"],
        })
        if amt is None:
            all_known = False
        else:
            known_subtotal += amt
    fare = {
        "currency": "PHP",
        "per_leg": per_leg,
        "total_centavos": known_subtotal if all_known and ride_segs else None,
        "known_subtotal_centavos": known_subtotal,
        "total_is_complete": bool(all_known and ride_segs),
    }

    # Time aggregation. Walking + waiting unknown here (no pedestrian/freq data).
    riding_known = all(s["duration_seconds"] is not None for s in ride_segs) and bool(ride_segs)
    riding_total = sum(s["duration_seconds"] for s in ride_segs) if riding_known else None
    known_riding = sum(s["duration_seconds"] for s in ride_segs if s["duration_seconds"] is not None)
    uncertainty = []
    if not riding_known:
        uncertainty.append("Riding time unknown for at least one leg.")
    uncertainty.append("Waiting time unknown (no verified frequency data).")
    uncertainty.append("Walking distance/time approximate (straight-line only).")
    time = {
        "walking_seconds": None,
        "waiting_seconds": None,
        "riding_seconds": riding_total,
        "total_seconds": None,  # never complete without walking+waiting
        "known_subtotal_seconds": known_riding,
        "total_is_complete": False,
        "uncertainty_notes": uncertainty,
    }

    # Public evidence (dedup source ids across ride legs).
    ev_source_ids = sorted({sid for s in ride_segs for sid in s["source_ids"]})
    # The journey is only as trusted as its weakest ride leg.
    leg_statuses = {s["verification_status"] for s in ride_segs}
    evidence = {
        "source_ids": ev_source_ids,
        "references": [network.sources.get(sid, {}) for sid in ev_source_ids],
        "verification_status": "verified" if leg_statuses == {"verified"} else "documented",
    }

    # Known walking distance for ranking fallback (sum straight-line of walks).
    walk_known = sum(s.get("straight_line_m", 0) for s in segments if s["mode"] == "walk")

    warnings = []
    if evidence["verification_status"] != "verified":
        warnings.append(
            "Built from documented (published/historic) data that is not field-verified; "
            "confirm the route is still operating before travelling."
        )
    if not fare["total_is_complete"]:
        warnings.append("Total fare incomplete: at least one leg has no verified fare.")

    return {
        "transfers": transfers,
        "labels": [],
        "segments": segments,
        "fare": fare,
        "time": time,
        "evidence": evidence,
        "warnings": warnings,
        # internal fields (stripped before output):
        "_dedup_key": _dedup_key(segments),
        "_walk_known_m": walk_known,
    }


def _dedup_key(segments: list[dict]) -> tuple:
    key = []
    for s in segments:
        if s["mode"] == "ride":
            key.append(("ride", s["route_pattern_id"], s["board_occurrence_id"], s["alight_occurrence_id"]))
        elif s["mode"] == "transfer_walk":
            key.append(("transfer", s.get("from_stop_id"), s.get("to_stop_id")))
    return tuple(key)


# --- Enumeration -----------------------------------------------------------


def _allowed_statuses(allow_documented: bool) -> frozenset[str]:
    return frozenset({"verified", "documented"} if allow_documented else {"verified"})


def _enumerate_direct(network, req, origin_stops, dest_stops, statuses, passenger_category, on):
    origin_ids = {c.stop_id for c in origin_stops}
    dest_ids = {c.stop_id for c in dest_stops}
    straight = {c.stop_id: c.straight_line_m for c in origin_stops}
    straight.update({c.stop_id: c.straight_line_m for c in dest_stops})
    options = []
    for pattern in network.patterns:
        if pattern.status not in statuses:
            continue
        route = network.routes[pattern.route_id]
        for b_stop in origin_ids:
            for board in _board_occurrences(pattern, b_stop):
                for a_stop in dest_ids:
                    for alight in _alight_occurrences(pattern, a_stop):
                        if alight.sequence <= board.sequence:
                            continue  # must go forward along the directed pattern
                        o_name = network.stops[b_stop].name
                        d_name = network.stops[a_stop].name
                        segs = [
                            _walk_segment("origin", o_name, straight.get(b_stop, 0.0)),
                            _ride_segment(network, pattern, route, board, alight,
                                          passenger_category=passenger_category, on=on),
                            _walk_segment(d_name, "destination", straight.get(a_stop, 0.0)),
                        ]
                        options.append(_assemble_option(network, segs, transfers=0))
    return options


def _enumerate_one_transfer(network, req, origin_stops, dest_stops, statuses,
                            passenger_category, on):
    origin_ids = {c.stop_id for c in origin_stops}
    dest_ids = {c.stop_id for c in dest_stops}
    straight = {c.stop_id: c.straight_line_m for c in origin_stops}
    straight.update({c.stop_id: c.straight_line_m for c in dest_stops})

    # Directed transfer index: from_stop -> list[(to_stop, transfer)]
    transfers_by_from: dict[str, list] = {}
    for t in network.transfers:
        if t.status not in statuses:
            continue
        transfers_by_from.setdefault(t.from_stop_id, []).append(t)

    verified_patterns = [p for p in network.patterns if p.status in statuses]
    options = []
    for p1 in verified_patterns:
        r1 = network.routes[p1.route_id]
        for ob in origin_ids:
            for board1 in _board_occurrences(p1, ob):
                # alight p1 at any later occurrence that has an outgoing transfer
                for alight1 in p1.stops:
                    if alight1.sequence <= board1.sequence or not alight1.can_alight:
                        continue
                    for t in transfers_by_from.get(alight1.stop_id, []):
                        for p2 in verified_patterns:
                            if p2.id == p1.id:
                                continue
                            r2 = network.routes[p2.route_id]
                            for board2 in _board_occurrences(p2, t.to_stop_id):
                                for db in dest_ids:
                                    for alight2 in _alight_occurrences(p2, db):
                                        if alight2.sequence <= board2.sequence:
                                            continue
                                        segs = _build_transfer_segments(
                                            network, p1, r1, board1, alight1,
                                            t, p2, r2, board2, alight2,
                                            straight, passenger_category, on,
                                        )
                                        options.append(_assemble_option(network, segs, transfers=1))
    return options


def _build_transfer_segments(network, p1, r1, board1, alight1, t, p2, r2, board2, alight2,
                             straight, passenger_category, on):
    o_name = network.stops[board1.stop_id].name
    d_name = network.stops[alight2.stop_id].name
    from_name = network.stops[t.from_stop_id].name
    to_name = network.stops[t.to_stop_id].name
    transfer_seg = {
        "mode": "transfer_walk",
        "from_stop_id": t.from_stop_id,
        "to_stop_id": t.to_stop_id,
        "instruction": f"Transfer: walk from {from_name} to {to_name}.",
        "distance_m": t.distance_m,
        "duration_seconds": t.duration_seconds,
        "estimate_basis": "sourced_observation" if t.duration_seconds is not None else None,
        "source_ids": list(t.source_ids),
    }
    return [
        _walk_segment("origin", o_name, straight.get(board1.stop_id, 0.0)),
        _ride_segment(network, p1, r1, board1, alight1,
                      passenger_category=passenger_category, on=on),
        transfer_seg,
        _ride_segment(network, p2, r2, board2, alight2,
                      passenger_category=passenger_category, on=on),
        _walk_segment(d_name, "destination", straight.get(alight2.stop_id, 0.0)),
    ]


# --- Dedup & ranking -------------------------------------------------------


def _deduplicate(options: list[dict]) -> list[dict]:
    seen = {}
    for opt in options:
        key = opt["_dedup_key"]
        if key not in seen:
            seen[key] = opt
    return list(seen.values())


def _rank(options: list[dict], sort_by: str) -> tuple[list[dict], dict]:
    applied = sort_by
    warning = None

    def fewest_key(o):
        return (o["transfers"], o["_walk_known_m"], o["_dedup_key"])

    if sort_by == "cheapest":
        comparable = [o for o in options if o["fare"]["total_is_complete"]]
        if len(comparable) == len(options) and options:
            options.sort(key=lambda o: (o["fare"]["total_centavos"], o["transfers"], o["_dedup_key"]))
        else:
            applied = "fewest_transfers"
            warning = "Cannot fairly rank by cheapest: some fares are unknown. Fell back to fewest_transfers."
            options.sort(key=fewest_key)
    elif sort_by == "fastest":
        comparable = [o for o in options if o["time"]["total_is_complete"]]
        if len(comparable) == len(options) and options:
            options.sort(key=lambda o: (o["time"]["total_seconds"], o["transfers"], o["_dedup_key"]))
        else:
            applied = "fewest_transfers"
            warning = "Cannot fairly rank by fastest: some durations are unknown. Fell back to fewest_transfers."
            options.sort(key=fewest_key)
    elif sort_by == "least_walking":
        # Unknown walking distance cannot win. All walks here are straight-line
        # only; treat as not fairly comparable -> fallback.
        applied = "fewest_transfers"
        warning = "Cannot fairly rank by least_walking: walking distances are approximate. Fell back to fewest_transfers."
        options.sort(key=fewest_key)
    else:  # fewest_transfers
        options.sort(key=fewest_key)

    ranking = {"requested": sort_by, "applied": applied, "warning": warning}
    return options, ranking


def _apply_labels(options: list[dict]) -> None:
    if not options:
        return
    # fewest_transfers label -> all options with the minimum transfer count
    min_t = min(o["transfers"] for o in options)
    for o in options:
        if o["transfers"] == min_t:
            o["labels"].append("fewest_transfers")
    # cheapest -> only among complete fares
    complete_fares = [o for o in options if o["fare"]["total_is_complete"]]
    if complete_fares:
        cheapest = min(o["fare"]["total_centavos"] for o in complete_fares)
        for o in complete_fares:
            if o["fare"]["total_centavos"] == cheapest:
                o["labels"].append("cheapest")
    # fastest -> only among complete durations
    complete_times = [o for o in options if o["time"]["total_is_complete"]]
    if complete_times:
        fastest = min(o["time"]["total_seconds"] for o in complete_times)
        for o in complete_times:
            if o["time"]["total_seconds"] == fastest:
                o["labels"].append("fastest")


def _strip_internal(options: list[dict], response_prefix: str) -> list[dict]:
    out = []
    for i, o in enumerate(options):
        o = dict(o)
        o.pop("_dedup_key", None)
        o.pop("_walk_known_m", None)
        o["id"] = f"{response_prefix}-{i+1}"
        out.append(o)
    return out


# --- Public entry point ----------------------------------------------------


def plan_journeys(network: Network, req: PlanRequest, *, config: Optional[dict] = None,
                  response_prefix: str = "opt") -> PlanResult:
    """Plan journeys for one request. Call again with swapped endpoints for return."""
    _validate_request(req)
    config = config or {}
    radius_m = float(config.get("STOP_SEARCH_RADIUS_M", 500))
    allow_documented = bool(config.get("ALLOW_DOCUMENTED", False))
    passenger_category = config.get("passenger_category", "regular")
    on = req.query_date or date.today()
    statuses = _allowed_statuses(allow_documented)

    # Same-location short circuit.
    if haversine_m(req.origin.latitude, req.origin.longitude,
                   req.destination.latitude, req.destination.longitude) <= _SAME_POINT_EPS_M:
        return PlanResult(
            request_coverage_status=LIMITED, reason=REASON_SAME_LOCATION,
            journey_options=[],
            ranking={"requested": req.sort_by, "applied": req.sort_by, "warning": None},
            warnings=["Origin and destination are effectively the same location."],
        )

    # Stops follow the same gate as patterns (documented only when enabled).
    origin_stops = _eligible_stops(network, req.origin, radius_m=radius_m, boarding=True,
                                   allowed_statuses=statuses)
    dest_stops = _eligible_stops(network, req.destination, radius_m=radius_m, boarding=False,
                                 allowed_statuses=statuses)

    has_any_verified_pattern = any(p.status in statuses for p in network.patterns)

    if not origin_stops or not dest_stops:
        status = LIMITED if has_any_verified_pattern else LIMITED
        return PlanResult(
            request_coverage_status=status, reason=REASON_INSUFFICIENT,
            journey_options=[],
            ranking={"requested": req.sort_by, "applied": req.sort_by, "warning": None},
            warnings=["No eligible verified boarding/alighting stop near one or both endpoints."],
        )

    options = _enumerate_direct(network, req, origin_stops, dest_stops, statuses,
                                passenger_category, on)
    if req.max_transfers >= 1:
        options += _enumerate_one_transfer(network, req, origin_stops, dest_stops, statuses,
                                           passenger_category, on)

    options = _deduplicate(options)

    if not options:
        return PlanResult(
            request_coverage_status=LIMITED, reason=REASON_NO_JOURNEY,
            journey_options=[],
            ranking={"requested": req.sort_by, "applied": req.sort_by, "warning": None},
            warnings=["No verified journey is available in the current dataset within MVP limits."],
        )

    options, ranking = _rank(options, req.sort_by)
    options = options[: req.limit]
    _apply_labels(options)
    public = _strip_internal(options, response_prefix)

    warnings = []
    if allow_documented:
        warnings.append(
            "Results may include historic/documented data that is NOT field-verified for current service."
        )
    coverage = WITHIN if not allow_documented else LIMITED
    return PlanResult(
        request_coverage_status=coverage, reason=None,
        journey_options=public, ranking=ranking, warnings=warnings,
    )
