"""Build journey segments and totals without inventing missing evidence."""
from __future__ import annotations

from typing import Optional

from .fares import compute_leg_fare_centavos, resolve_fare_rule
from .journey_types import Network, TransferData
from .ranking import journey_key
from .search_types import RideLeg, SearchContext, TransferCandidate


def _segment_metrics(leg: RideLeg) -> tuple[int, Optional[int]]:
    """Return ride distance and time; any missing segment makes time unknown."""
    pattern, board, alight = leg.pattern, leg.board, leg.alight
    distance_m = max(0, alight.distance_along_m - board.distance_along_m)
    occurrence_by_sequence = {o.sequence: o for o in pattern.stops}
    sequences = sorted(occurrence_by_sequence)
    segment_by_pair = {
        (s.from_occurrence_id, s.to_occurrence_id): s
        for s in pattern.segments
    }
    between = [
        sequence for sequence in sequences
        if board.sequence <= sequence <= alight.sequence
    ]
    riding_seconds = 0
    riding_known = True
    for start, end in zip(between, between[1:]):
        segment = segment_by_pair.get((
            occurrence_by_sequence[start].id,
            occurrence_by_sequence[end].id,
        ))
        if segment is None or segment.riding_seconds is None:
            riding_known = False
        else:
            riding_seconds += segment.riding_seconds
    return distance_m, riding_seconds if riding_known else None


def _leg_fare(context: SearchContext, leg: RideLeg, distance_m: int) -> dict:
    route = context.network.routes[leg.pattern.route_id]
    rule = resolve_fare_rule(
        context.network, route=route, pattern_id=leg.pattern.id,
        passenger_category=context.passenger_category, on=context.on,
    )
    amount = compute_leg_fare_centavos(rule, distance_m) if rule else None
    return {
        "amount_centavos": amount,
        "rule_id": rule.id if rule else None,
        "passenger_category": context.passenger_category,
        "source_ids": list(rule.source_ids) if rule else [],
        "effective_date": rule.valid_from.isoformat() if rule else None,
        "assumptions": None if rule else "No verified fare rule for this leg.",
    }


def _ride_segment(context: SearchContext, leg: RideLeg) -> dict:
    pattern, board, alight = leg.pattern, leg.board, leg.alight
    route = context.network.routes[pattern.route_id]
    distance_m, riding_seconds = _segment_metrics(leg)
    board_stop = context.network.stops[board.stop_id]
    alight_stop = context.network.stops[alight.stop_id]
    fare = _leg_fare(context, leg, distance_m)
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
        "board_sequence": board.sequence,
        "alight_sequence": alight.sequence,
        "start": {"latitude": board_stop.latitude, "longitude": board_stop.longitude},
        "end": {"latitude": alight_stop.latitude, "longitude": alight_stop.longitude},
        "geometry": None,  # Sourced route shapes are attached at the API layer.
        "instruction": (
            f"Board {route.code} ({pattern.direction}) at {board_stop.name}; "
            f"alight at {alight_stop.name}."
        ),
        "distance_m": distance_m,
        "duration_seconds": riding_seconds,
        "estimate_basis": "sourced_observation" if riding_seconds is not None else None,
        "waiting_seconds": None,
        "fare": fare,
        "source_ids": source_ids,
    }


def _walk_segment(from_name: str, to_name: str, straight_m: float) -> dict:
    """Access or egress estimate; a straight line is not a verified walk."""
    return {
        "mode": "walk",
        "instruction": f"Walk from {from_name} to {to_name} (approximate; not a verified route).",
        "distance_m": None,
        "duration_seconds": None,
        "estimate_basis": "straight_line_approx",
        "straight_line_m": round(straight_m, 1),
        "source_ids": [],
    }


def _transfer_segment(network: Network, connection: TransferData) -> dict:
    from_stop = network.stops[connection.from_stop_id]
    to_stop = network.stops[connection.to_stop_id]
    return {
        "mode": "transfer_walk",
        "from_stop_id": connection.from_stop_id,
        "to_stop_id": connection.to_stop_id,
        "start": {"latitude": from_stop.latitude, "longitude": from_stop.longitude},
        "end": {"latitude": to_stop.latitude, "longitude": to_stop.longitude},
        "instruction": f"Transfer: walk from {from_stop.name} to {to_stop.name}.",
        "distance_m": connection.distance_m,
        "duration_seconds": connection.duration_seconds,
        "estimate_basis": (
            "sourced_observation" if connection.duration_seconds is not None else None
        ),
        "source_ids": list(connection.source_ids),
    }


def _fare_total(ride_segments: list[dict]) -> dict:
    """A total is complete only when every ride has a known fare."""
    per_leg = []
    known_subtotal = 0
    all_known = True
    for segment in ride_segments:
        fare = segment["fare"]
        amount = fare["amount_centavos"]
        per_leg.append({
            "segment_route_pattern_id": segment["route_pattern_id"],
            "amount_centavos": amount,
            "rule_id": fare["rule_id"],
            "passenger_category": fare["passenger_category"],
            "source_ids": fare["source_ids"],
            "effective_date": fare["effective_date"],
            "assumptions": fare["assumptions"],
        })
        if amount is None:
            all_known = False
        else:
            known_subtotal += amount
    return {
        "currency": "PHP",
        "per_leg": per_leg,
        "total_centavos": known_subtotal if all_known and ride_segments else None,
        "known_subtotal_centavos": known_subtotal,
        "total_is_complete": bool(all_known and ride_segments),
    }


def _time_total(ride_segments: list[dict]) -> dict:
    """Keep the ride subtotal separate from unknown walking and waiting."""
    riding_known = (
        all(s["duration_seconds"] is not None for s in ride_segments)
        and bool(ride_segments)
    )
    riding_total = (
        sum(s["duration_seconds"] for s in ride_segments) if riding_known else None
    )
    known_riding = sum(
        s["duration_seconds"] for s in ride_segments
        if s["duration_seconds"] is not None
    )
    uncertainty = []
    if not riding_known:
        uncertainty.append("Riding time unknown for at least one leg.")
    uncertainty.append("Waiting time unknown (no verified frequency data).")
    uncertainty.append("Walking distance/time approximate (straight-line only).")
    return {
        "walking_seconds": None,
        "waiting_seconds": None,
        "riding_seconds": riding_total,
        "total_seconds": None,
        "known_subtotal_seconds": known_riding,
        "total_is_complete": False,
        "uncertainty_notes": uncertainty,
    }


def _journey_evidence(network: Network, ride_segments: list[dict]) -> dict:
    source_ids = sorted({sid for s in ride_segments for sid in s["source_ids"]})
    # The journey is only as trusted as its weakest ride leg.
    leg_statuses = {s["verification_status"] for s in ride_segments}
    return {
        "source_ids": source_ids,
        "references": [network.sources.get(sid, {}) for sid in source_ids],
        "verification_status": "verified" if leg_statuses == {"verified"} else "documented",
    }


def _option_warnings(evidence: dict, fare: dict) -> list[str]:
    warnings = []
    if evidence["verification_status"] != "verified":
        warnings.append(
            "Built from documented (published/historic) data that is not field-verified; "
            "confirm the route is still operating before travelling."
        )
    if not fare["total_is_complete"]:
        warnings.append("Total fare incomplete: at least one leg has no verified fare.")
    return warnings


def _assemble_option(network: Network, segments: list[dict], transfers: int) -> dict:
    ride_segments = [s for s in segments if s["mode"] == "ride"]
    fare = _fare_total(ride_segments)
    time = _time_total(ride_segments)
    evidence = _journey_evidence(network, ride_segments)
    walk_known = sum(
        s.get("straight_line_m", 0) for s in segments if s["mode"] == "walk"
    )
    return {
        "transfers": transfers,
        "labels": [],
        "segments": segments,
        "fare": fare,
        "time": time,
        "evidence": evidence,
        "warnings": _option_warnings(evidence, fare),
        # These ranking fields are removed before returning the response.
        "_dedup_key": journey_key(segments),
        "_walk_known_m": walk_known,
        "_ride_m": sum(s["distance_m"] or 0 for s in ride_segments),
    }


def assemble_direct_option(context: SearchContext, leg: RideLeg) -> dict:
    stops = context.network.stops
    straight = context.straight_line_by_stop
    segments = [
        _walk_segment(
            "origin", stops[leg.board.stop_id].name,
            straight.get(leg.board.stop_id, 0.0),
        ),
        _ride_segment(context, leg),
        _walk_segment(
            stops[leg.alight.stop_id].name, "destination",
            straight.get(leg.alight.stop_id, 0.0),
        ),
    ]
    return _assemble_option(context.network, segments, transfers=0)


def assemble_transfer_option(
    context: SearchContext, candidate: TransferCandidate,
) -> dict:
    first, second = candidate.first_leg, candidate.second_leg
    stops = context.network.stops
    straight = context.straight_line_by_stop
    transfer_segment = _transfer_segment(context.network, candidate.connection)
    segments = [
        _walk_segment(
            "origin", stops[first.board.stop_id].name,
            straight.get(first.board.stop_id, 0.0),
        ),
        _ride_segment(context, first),
        transfer_segment,
        _ride_segment(context, second),
        _walk_segment(
            stops[second.alight.stop_id].name, "destination",
            straight.get(second.alight.stop_id, 0.0),
        ),
    ]
    return _assemble_option(context.network, segments, transfers=1)
