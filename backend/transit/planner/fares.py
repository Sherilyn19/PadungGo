"""Fare computation. Data-driven only; unavailable fares return None (not 0)."""
from __future__ import annotations

import math
from datetime import date
from typing import Optional

from .journey_types import FarePolicy, Network, RouteData


def _applicable(f: FarePolicy, *, vehicle_class: str, route_id: str, pattern_id: str,
                passenger_category: str, on: date) -> bool:
    if f.status != "verified":
        return False
    if f.passenger_category != passenger_category:
        return False
    if f.valid_from > on:
        return False
    if f.valid_until is not None and f.valid_until < on:
        return False
    # Scope: pattern rule must match this pattern; route rule must match route;
    # class rule applies by vehicle class.
    if f.pattern_id is not None and f.pattern_id != pattern_id:
        return False
    if f.route_id is not None and f.route_id != route_id:
        return False
    if f.vehicle_class != vehicle_class:
        return False
    return True


def resolve_fare_rule(
    network: Network,
    *,
    route: RouteData,
    pattern_id: str,
    passenger_category: str,
    on: date,
) -> Optional[FarePolicy]:
    """Most-specific applicable verified rule. Reject ambiguous equal-specificity.

    Returns None if no verified rule applies, or if two equally-specific rules
    conflict (ambiguous => treat fare as unknown rather than pick arbitrarily).
    """
    candidates = [
        f for f in network.fares
        if _applicable(
            f, vehicle_class=route.vehicle_class, route_id=route.id,
            pattern_id=pattern_id, passenger_category=passenger_category, on=on,
        )
    ]
    if not candidates:
        return None
    top = max(c.specificity for c in candidates)
    top_rules = [c for c in candidates if c.specificity == top]
    if len(top_rules) > 1:
        # Ambiguous equal-specificity: do not guess.
        return None
    return top_rules[0]


def compute_leg_fare_centavos(rule: FarePolicy, distance_m: int) -> Optional[int]:
    """Apply a verified policy to a travelled leg distance. None if uncomputable."""
    p = rule.policy
    if rule.kind == "flat":
        amount = p.get("amount_centavos")
        return amount if isinstance(amount, int) else None
    if rule.kind == "distance_band":
        try:
            base = int(p["base_centavos"])
            base_dist = int(p["base_distance_m"])
            inc = int(p["increment_centavos"])
            inc_dist = int(p["increment_distance_m"])
        except (KeyError, TypeError, ValueError):
            return None
        if inc_dist <= 0:
            return None
        extra = max(0, distance_m - base_dist)
        bands = math.ceil(extra / inc_dist) if extra > 0 else 0
        amount = base + bands * inc
        rounding = p.get("rounding_centavos")
        if isinstance(rounding, int) and rounding > 0:
            amount = int(round(amount / rounding) * rounding)
        return amount
    return None
