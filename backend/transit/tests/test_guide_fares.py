"""Guide estimates checked against printed tables and owner distance rules."""
from datetime import date

import pytest

from transit.planner.guide_fares import guide_fare_estimate
from transit.tests.test_fare_guide_2026 import FARE_ROWS


EFFECTIVE_DATE = date(2026, 9, 28)


def estimate(distance_m, vehicle_class="jeepney", on=EFFECTIVE_DATE):
    return guide_fare_estimate(
        distance_m=distance_m,
        vehicle_class=vehicle_class,
        on=on,
    )


@pytest.mark.parametrize("row", FARE_ROWS, ids=lambda row: f"{row[0]}km")
@pytest.mark.parametrize(
    "vehicle,column,index",
    (
        ("traditional", "regular", 1),
        ("traditional", "discounted", 2),
        ("modern", "regular", 3),
        ("modern", "discounted", 4),
    ),
)
def test_matches_printed_table(row, vehicle, column, index):
    # FARE_ROWS contains literal printed amounts, not computed expectations.
    result = estimate(row[0] * 1000)
    amount = result["amounts_centavos"][vehicle][column]

    assert result["status"] == "available"
    assert amount == row[index]
    assert type(amount) is int
    assert amount % 25 == 0


@pytest.mark.parametrize(
    "distance_m,expected_km",
    (
        (1, 1),
        (3000, 3),
        (3100, 4),
        (4000, 4),
        (4001, 5),
        (5500, 6),
        (5900, 6),
        (6000, 6),
        (6010, 7),
        (9990, 10),
    ),
)
def test_owner_ceiling_rule(distance_m, expected_km):
    result = estimate(distance_m)

    assert result["status"] == "available"
    assert result["chargeable_km"] == expected_km


def test_available_response_has_exact_contract_and_six_km_amounts():
    assert estimate(5900) == {
        "status": "available",
        "reason": None,
        "guide_effective_date": "2026-09-28",
        "chargeable_km": 6,
        "known_vehicle_type": None,
        "amounts_centavos": {
            "traditional": {"regular": 1800, "discounted": 1450},
            "modern": {"regular": 2175, "discounted": 1750},
        },
    }


def test_partial_seventh_kilometre():
    result = estimate(6010)

    assert result["amounts_centavos"]["traditional"]["regular"] == 2000


def test_discount_uses_printed_column_not_rounded_regular_fare():
    amounts = estimate(6000)["amounts_centavos"]["modern"]

    assert amounts["regular"] == 2175
    assert amounts["discounted"] == 1750
    assert amounts["discounted"] != 1740


def test_last_supported_distance():
    assert estimate(50000) == {
        "status": "available",
        "reason": None,
        "guide_effective_date": "2026-09-28",
        "chargeable_km": 50,
        "known_vehicle_type": None,
        "amounts_centavos": {
            "traditional": {"regular": 10600, "discounted": 8475},
            "modern": {"regular": 12750, "discounted": 10200},
        },
    }


@pytest.mark.parametrize(
    "distance_m,vehicle_class,on,reason",
    (
        (None, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (0, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (-1, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (6000.0, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        ("6000", "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (True, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (False, "jeepney", EFFECTIVE_DATE, "missing_distance"),
        (50001, "jeepney", EFFECTIVE_DATE, "beyond_guide_range"),
        (6000, "bus", EFFECTIVE_DATE, "not_puj"),
        (6000, "jeepney", date(2026, 9, 27), "guide_not_in_effect"),
        # Preserve the contract's reason precedence when failures overlap.
        (None, "bus", date(2026, 9, 27), "missing_distance"),
        (50001, "bus", date(2026, 9, 27), "beyond_guide_range"),
        (6000, "bus", date(2026, 9, 27), "not_puj"),
    ),
)
def test_unavailable_response(distance_m, vehicle_class, on, reason):
    assert estimate(distance_m, vehicle_class, on) == {
        "status": "unavailable",
        "reason": reason,
        "guide_effective_date": "2026-09-28",
        "chargeable_km": None,
        "known_vehicle_type": None,
        "amounts_centavos": None,
    }


@pytest.mark.parametrize("vehicle_class", ("jeepney", "modern_puv", "mixed"))
def test_route_label_does_not_select_a_guide(vehicle_class):
    result = estimate(6000, vehicle_class)

    assert result["status"] == "available"
    assert result["known_vehicle_type"] is None
    assert result["amounts_centavos"] == {
        "traditional": {"regular": 1800, "discounted": 1450},
        "modern": {"regular": 2175, "discounted": 1750},
    }


@pytest.mark.parametrize("on", (EFFECTIVE_DATE, date(2026, 10, 22)))
def test_guide_available_on_and_after_effective_date(on):
    assert estimate(6000, on=on)["status"] == "available"


def test_each_ride_gets_its_own_base_distance_and_ceiling():
    first = estimate(3100)
    second = estimate(3100)

    assert first["chargeable_km"] == 4
    assert second["chargeable_km"] == 4
    assert first["amounts_centavos"]["traditional"]["regular"] == 1400
    assert second["amounts_centavos"]["modern"]["regular"] == 1700