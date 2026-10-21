"""Quotation rules tested with synthetic services, not production claims."""
from dataclasses import replace
from datetime import date

import pytest

from transit.planner.fare_quotes import quote_leg_fare
from transit.tests.planner_fixtures import base_network


ON = date(2026, 10, 21)


def _quote(network, distance_m=5000, category="regular"):
    return quote_leg_fare(
        network,
        pattern=network.patterns[0],
        distance_m=distance_m,
        passenger_category=category,
        on=ON,
    )


def _band_network(category="regular"):
    network = base_network()
    base, increment = (1120, 160) if category == "student" else (1400, 200)
    network.fares = [
        replace(
            network.fares[0],
            kind="distance_band",
            passenger_category=category,
            valid_from=date(2026, 9, 28),
            policy={
                "base_centavos": base,
                "base_distance_m": 4000,
                "increment_centavos": increment,
                "increment_distance_m": 1000,
                "rounding_centavos": 25,
                "max_distance_m": 50000,
            },
        )
    ]
    return network


def test_supported_flat_fare_is_exact():
    quote = _quote(base_network())

    assert quote.amount_centavos == 1300
    assert quote.status == "exact"
    assert quote.reason is None
    assert quote.rule.id == "F-1"


@pytest.mark.parametrize(
    "distance_m,expected",
    [(3000, 1400), (4000, 1400), (5000, 1600), (50000, 10600)],
)
def test_supported_distance_fare_is_approximate(distance_m, expected):
    quote = _quote(_band_network(), distance_m)

    assert quote.amount_centavos == expected
    assert quote.status == "approximate"
    assert "billable distance may differ" in quote.reason


def test_discount_uses_its_own_published_policy():
    quote = _quote(_band_network("student"), 6000, "student")

    assert quote.amount_centavos == 1450
    assert quote.status == "approximate"
    assert quote.rule.passenger_category == "student"


@pytest.mark.parametrize("distance_m", [4001, 4055])
def test_fractional_distance_is_not_silently_rounded_up(distance_m):
    quote = _quote(_band_network(), distance_m)

    assert quote.amount_centavos is None
    assert quote.status == "unavailable"
    assert "part of a distance band" in quote.reason


def test_missing_and_exceeded_source_coverage_are_not_guessed():
    network = _band_network()
    quote = _quote(network, 51000)

    assert quote.amount_centavos is None
    assert "exceeds the supported fare range" in quote.reason

    del network.fares[0].policy["max_distance_m"]
    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.reason == "Fare distance coverage is not recorded."


def test_documented_pattern_is_not_upgraded_by_a_fare_rule():
    network = base_network()
    network.patterns[0] = replace(network.patterns[0], status="documented")

    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.status == "unavailable"
    assert quote.reason == "Route verification is incomplete."


def test_missing_fare_evidence_prevents_a_price():
    network = base_network()
    network.fares[0] = replace(network.fares[0], source_ids=())

    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.reason == "Fare evidence is incomplete."


def test_mixed_fleet_does_not_receive_a_single_vehicle_price():
    network = base_network()
    network.routes["R-A"] = replace(
        network.routes["R-A"], vehicle_class="mixed"
    )

    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.status == "unavailable"
    assert "traditional and modern" in quote.reason


def test_conflicting_rules_return_a_broad_truthful_reason():
    network = base_network()
    network.fares.append(replace(network.fares[0], id="conflicting-rule"))

    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.reason == "No supported fare calculation."


@pytest.mark.parametrize("invalid_base", [True, -1, "1400"])
def test_invalid_policy_values_are_not_coerced(invalid_base):
    network = _band_network()
    network.fares[0].policy["base_centavos"] = invalid_base

    quote = _quote(network)

    assert quote.amount_centavos is None
    assert quote.reason == "Fare policy needs review."


def test_money_rounding_tie_is_not_assumed():
    network = _band_network()
    network.fares[0].policy.update(
        base_centavos=1400,
        increment_centavos=25,
        rounding_centavos=50,
    )

    quote = _quote(network, 5000)

    assert quote.amount_centavos is None
    assert quote.reason == "Fare rounding needs confirmation."
