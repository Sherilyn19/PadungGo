"""Combine classified ride fares without hiding missing amounts."""
from __future__ import annotations


def _normalise_leg(segment: dict) -> dict:
    """Keep public fare metadata and reject inconsistent numeric results."""
    fare = segment["fare"]
    amount = fare.get("amount_centavos")
    status = fare.get("status")
    reason = fare.get("reason")
    reason = reason.strip() if isinstance(reason, str) else None

    valid_amount = type(amount) is int and amount >= 0
    supported_status = status in {"exact", "approximate"}

    if not valid_amount or not supported_status:
        amount = None
        reason = (
            reason or "No supported fare calculation."
            if status == "unavailable"
            else "No supported fare calculation."
        )
        status = "unavailable"

    return {
        "segment_route_pattern_id": segment["route_pattern_id"],
        "amount_centavos": amount,
        "rule_id": fare.get("rule_id"),
        "passenger_category": fare.get("passenger_category"),
        "source_ids": list(fare.get("source_ids", [])),
        "effective_date": fare.get("effective_date"),
        "assumptions": fare.get("assumptions"),
        "status": status,
        "reason": reason or None,
    }


def summarise_fares(ride_segments: list[dict]) -> dict:
    """A complete total requires a supported amount for every ride."""
    per_leg = [_normalise_leg(segment) for segment in ride_segments]
    known_subtotal = sum(
        fare["amount_centavos"]
        for fare in per_leg
        if fare["amount_centavos"] is not None
    )
    complete = bool(per_leg) and all(
        fare["status"] in {"exact", "approximate"} for fare in per_leg
    )

    if not complete:
        status = "unavailable"
        reason = (
            "A fare could not be calculated for every ride."
            if per_leg
            else "No ride fare to calculate."
        )
    elif any(fare["status"] == "approximate" for fare in per_leg):
        status = "approximate"
        reason = "Includes an approximate fare. See the ride steps for details."
    else:
        status = "exact"
        reason = None

    return {
        "currency": "PHP",
        "per_leg": per_leg,
        "total_centavos": known_subtotal if complete else None,
        "known_subtotal_centavos": known_subtotal,
        "total_is_complete": complete,
        "status": status,
        "reason": reason,
    }
