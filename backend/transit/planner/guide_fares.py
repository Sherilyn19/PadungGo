"""Guide-based estimates, separate from verified fare quotes."""
from __future__ import annotations

from datetime import date


GUIDE_EFFECTIVE_DATE = date(2026, 9, 28)
MAX_CHARGEABLE_KM = 50
BASE_DISTANCE_KM = 4
ROUNDING_CENTAVOS = 25

# Printed add-on rates: docs/FARE_GUIDE_2026-09-28.md.
# "modern" covers aircon modern and electric PUJ only.
TRADITIONAL_REGULAR_BASE = 1400
TRADITIONAL_REGULAR_INCREMENT = 200
TRADITIONAL_DISCOUNTED_BASE = 1120
TRADITIONAL_DISCOUNTED_INCREMENT = 160
MODERN_REGULAR_BASE = 1700
MODERN_REGULAR_INCREMENT = 240
MODERN_DISCOUNTED_BASE = 1360
MODERN_DISCOUNTED_INCREMENT = 192


def _rounded_amount(base: int, increment: int, chargeable_km: int) -> int:
    extra_km = max(0, chargeable_km - BASE_DISTANCE_KM)
    unrounded = base + extra_km * increment
    quotient, remainder = divmod(unrounded, ROUNDING_CENTAVOS)
    # Integer centavos cannot tie halfway between multiples of an odd 25.
    return (
        quotient + (1 if 2 * remainder > ROUNDING_CENTAVOS else 0)
    ) * ROUNDING_CENTAVOS


def _unavailable(reason: str) -> dict:
    return {
        "status": "unavailable",
        "reason": reason,
        "guide_effective_date": GUIDE_EFFECTIVE_DATE.isoformat(),
        "chargeable_km": None,
        "known_vehicle_type": None,
        "amounts_centavos": None,
    }


def guide_fare_estimate(
    *,
    distance_m: int | None,
    vehicle_class: str,
    on: date,
) -> dict:
    """Return both guide options; never classify a route or alter its fare."""
    # bool is an int subclass, but is not a defensible distance.
    if (
        isinstance(distance_m, bool)
        or not isinstance(distance_m, int)
        or distance_m <= 0
    ):
        return _unavailable("missing_distance")

    # Owner-approved estimate policy: ceil each ride's integer metre distance.
    chargeable_km = -(-distance_m // 1000)
    if chargeable_km > MAX_CHARGEABLE_KM:
        return _unavailable("beyond_guide_range")

    if vehicle_class == "bus":
        return _unavailable("not_puj")

    if on < GUIDE_EFFECTIVE_DATE:
        return _unavailable("guide_not_in_effect")

    return {
        "status": "available",
        "reason": None,
        "guide_effective_date": GUIDE_EFFECTIVE_DATE.isoformat(),
        "chargeable_km": chargeable_km,
        # Current route labels do not establish which guide applies.
        "known_vehicle_type": None,
        "amounts_centavos": {
            "traditional": {
                "regular": _rounded_amount(
                    TRADITIONAL_REGULAR_BASE,
                    TRADITIONAL_REGULAR_INCREMENT,
                    chargeable_km,
                ),
                "discounted": _rounded_amount(
                    TRADITIONAL_DISCOUNTED_BASE,
                    TRADITIONAL_DISCOUNTED_INCREMENT,
                    chargeable_km,
                ),
            },
            "modern": {
                "regular": _rounded_amount(
                    MODERN_REGULAR_BASE,
                    MODERN_REGULAR_INCREMENT,
                    chargeable_km,
                ),
                "discounted": _rounded_amount(
                    MODERN_DISCOUNTED_BASE,
                    MODERN_DISCOUNTED_INCREMENT,
                    chargeable_km,
                ),
            },
        },
    }