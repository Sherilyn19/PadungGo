"""Classify fares without inventing vehicle or distance-policy evidence."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

from .fares import compute_leg_fare_centavos, resolve_fare_rule
from .journey_types import FarePolicy, Network, PatternData


@dataclass(frozen=True)
class FareQuote:
    amount_centavos: int | None
    status: Literal["exact", "approximate", "unavailable"]
    reason: str | None
    rule: FarePolicy | None


def _unavailable(
    reason: str = "No supported fare calculation.",
    rule: FarePolicy | None = None,
) -> FareQuote:
    return FareQuote(None, "unavailable", reason, rule)


def quote_leg_fare(
    network: Network,
    *,
    pattern: PatternData,
    distance_m: int,
    passenger_category: str,
    on: date,
) -> FareQuote:
    """Quote from the existing loader's evidence-filtered network."""
    route = network.routes.get(pattern.route_id)
    if route is None:
        return _unavailable()

    if route.vehicle_class == "mixed":
        return _unavailable(
            "This route runs traditional and modern vehicles; "
            "fare depends on the vehicle you board."
        )

    rule = resolve_fare_rule(
        network,
        route=route,
        pattern_id=pattern.id,
        passenger_category=passenger_category,
        on=on,
    )
    if rule is None:
        # The resolver may have rejected scope, dates or conflicting rules.
        # Do not claim a more specific cause than it actually reports.
        return _unavailable()

    if (
        pattern.status != "verified"
        or not pattern.has_verified_evidence
        or not pattern.evidence_source_ids
    ):
        return _unavailable("Route verification is incomplete.", rule)

    if not rule.source_ids:
        return _unavailable("Fare evidence is incomplete.", rule)

    if rule.currency != "PHP" or not isinstance(rule.policy, dict):
        return _unavailable("Fare policy needs review.", rule)

    policy = rule.policy
    if rule.kind == "flat":
        amount = policy.get("amount_centavos")
        if type(amount) is not int or amount < 0:
            return _unavailable("Fare policy needs review.", rule)
        return FareQuote(amount, "exact", None, rule)

    if rule.kind != "distance_band":
        return _unavailable("Fare policy needs review.", rule)

    if type(distance_m) is not int or distance_m <= 0:
        return _unavailable("Ride distance is not supported.", rule)

    keys = (
        "base_centavos",
        "base_distance_m",
        "increment_centavos",
        "increment_distance_m",
    )
    if any(
        type(policy.get(key)) is not int or policy[key] < 0
        for key in keys
    ):
        return _unavailable("Fare policy needs review.", rule)

    base_distance = policy["base_distance_m"]
    increment_distance = policy["increment_distance_m"]
    rounding = policy.get("rounding_centavos", 0)
    if (
        increment_distance <= 0
        or type(rounding) is not int
        or rounding < 0
    ):
        return _unavailable("Fare policy needs review.", rule)

    maximum_distance = policy.get("max_distance_m")
    if type(maximum_distance) is not int:
        return _unavailable("Fare distance coverage is not recorded.", rule)
    if maximum_distance <= 0 or maximum_distance < base_distance:
        return _unavailable("Fare policy needs review.", rule)
    if distance_m > maximum_distance:
        return _unavailable(
            "Ride distance exceeds the supported fare range.", rule
        )

    extra_distance = max(0, distance_m - base_distance)
    if extra_distance % increment_distance:
        return _unavailable(
            "Fare charging for part of a distance band is not confirmed.",
            rule,
        )

    # Do not silently choose a money-rounding tie convention either.
    bands = extra_distance // increment_distance
    unrounded = policy["base_centavos"] + bands * policy["increment_centavos"]
    if rounding and 2 * (unrounded % rounding) == rounding:
        return _unavailable("Fare rounding needs confirmation.", rule)

    amount = compute_leg_fare_centavos(rule, distance_m)
    if type(amount) is not int or amount < 0:
        return _unavailable("Fare policy needs review.", rule)

    return FareQuote(
        amount,
        "approximate",
        "Based on recorded ride distance; the billable distance may differ.",
        rule,
    )
