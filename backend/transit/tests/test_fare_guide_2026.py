"""LTFRB 2026-09-28 new-fare tables; pure planner tests, no database.

Sources and limitations: docs/FARE_GUIDE_2026-09-28.md.
Expected amounts are transcribed from page 1 of each supplied guide.
"""
from datetime import date

import pytest

from transit.planner.fares import compute_leg_fare_centavos
from transit.planner.journey_types import FarePolicy


# km, traditional regular, traditional discounted, modern regular,
# modern discounted. Amounts are integer centavos, not formula outputs.
FARE_ROWS = (
    (1, 1400, 1125, 1700, 1350),
    (2, 1400, 1125, 1700, 1350),
    (3, 1400, 1125, 1700, 1350),
    (4, 1400, 1125, 1700, 1350),
    (5, 1600, 1275, 1950, 1550),
    (6, 1800, 1450, 2175, 1750),
    (7, 2000, 1600, 2425, 1925),
    (8, 2200, 1750, 2650, 2125),
    (9, 2400, 1925, 2900, 2325),
    (10, 2600, 2075, 3150, 2500),
    (11, 2800, 2250, 3375, 2700),
    (12, 3000, 2400, 3625, 2900),
    (13, 3200, 2550, 3850, 3100),
    (14, 3400, 2725, 4100, 3275),
    (15, 3600, 2875, 4350, 3475),
    (16, 3800, 3050, 4575, 3675),
    (17, 4000, 3200, 4825, 3850),
    (18, 4200, 3350, 5050, 4050),
    (19, 4400, 3525, 5300, 4250),
    (20, 4600, 3675, 5550, 4425),
    (21, 4800, 3850, 5775, 4625),
    (22, 5000, 4000, 6025, 4825),
    (23, 5200, 4150, 6250, 5000),
    (24, 5400, 4325, 6500, 5200),
    (25, 5600, 4475, 6750, 5400),
    (26, 5800, 4650, 6975, 5575),
    (27, 6000, 4800, 7225, 5775),
    (28, 6200, 4950, 7450, 5975),
    (29, 6400, 5125, 7700, 6150),
    (30, 6600, 5275, 7950, 6350),
    (31, 6800, 5450, 8175, 6550),
    (32, 7000, 5600, 8425, 6725),
    (33, 7200, 5750, 8650, 6925),
    (34, 7400, 5925, 8900, 7125),
    (35, 7600, 6075, 9150, 7300),
    (36, 7800, 6250, 9375, 7500),
    (37, 8000, 6400, 9625, 7700),
    (38, 8200, 6550, 9850, 7900),
    (39, 8400, 6725, 10100, 8075),
    (40, 8600, 6875, 10350, 8275),
    (41, 8800, 7050, 10575, 8475),
    (42, 9000, 7200, 10825, 8650),
    (43, 9200, 7350, 11050, 8850),
    (44, 9400, 7525, 11300, 9050),
    (45, 9600, 7675, 11550, 9225),
    (46, 9800, 7850, 11775, 9425),
    (47, 10000, 8000, 12025, 9625),
    (48, 10200, 8150, 12250, 9800),
    (49, 10400, 8325, 12500, 10000),
    (50, 10600, 8475, 12750, 10200),
)

# Each discounted base/increment is explicitly printed in its guide.
POLICY_INPUTS = {
    "traditional_regular": ("jeepney", "regular", 1400, 200, 1),
    "traditional_discounted": ("jeepney", "student", 1120, 160, 2),
    "modern_regular": ("modern_puv", "regular", 1700, 240, 3),
    "modern_discounted": ("modern_puv", "student", 1360, 192, 4),
}


def make_policy(policy_name):
    vehicle_class, category, base, increment, _ = POLICY_INPUTS[policy_name]
    return FarePolicy(
        id=f"test-{policy_name}",
        vehicle_class=vehicle_class,
        route_id=f"test-route-{vehicle_class}",
        pattern_id=None,
        passenger_category=category,
        currency="PHP",
        kind="distance_band",
        policy={
            "base_centavos": base,
            "base_distance_m": 4000,
            "increment_centavos": increment,
            "increment_distance_m": 1000,
            "rounding_centavos": 25,
        },
        valid_from=date(2026, 9, 28),
        valid_until=None,
        status="verified",
    )


@pytest.mark.parametrize("policy_name", tuple(POLICY_INPUTS))
@pytest.mark.parametrize("row", FARE_ROWS, ids=lambda row: f"{row[0]}km")
def test_matches_official_new_fare_table(policy_name, row):
    rule = make_policy(policy_name)
    expected_column = POLICY_INPUTS[policy_name][4]

    assert compute_leg_fare_centavos(rule, row[0] * 1000) == row[expected_column]


@pytest.mark.parametrize(
    "policy_name,expected_base,expected_next",
    (
        ("traditional_regular", 1400, 1600),
        ("traditional_discounted", 1125, 1275),
        ("modern_regular", 1700, 1950),
        ("modern_discounted", 1350, 1550),
    ),
)
@pytest.mark.parametrize("distance_m", (4000, 4001, 5000))
def test_base_boundary_preserves_existing_distance_behavior(
    policy_name, expected_base, expected_next, distance_m
):
    # The PDFs do not define fractional kilometres. At 4001 m this checks
    # backward compatibility, not an officially established fare.
    rule = make_policy(policy_name)
    expected = expected_base if distance_m == 4000 else expected_next

    assert compute_leg_fare_centavos(rule, distance_m) == expected


def test_traditional_4055m_preserves_existing_unconfirmed_ceil_behavior():
    # Keep the demo behavior unchanged pending LTFRB distance clarification.
    rule = make_policy("traditional_regular")

    assert compute_leg_fare_centavos(rule, 4055) == 1600