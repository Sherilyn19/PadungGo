"""Exercise fare classification through the planner using synthetic services."""
from dataclasses import replace
from datetime import date

from transit.planner import plan_journeys
from transit.planner.journey_types import Endpoint, PlanRequest
from transit.tests.planner_fixtures import base_network


def _plan(network, *, transfer=False):
    destination = (
        Endpoint(latitude=10.3005, longitude=123.936)
        if transfer
        else Endpoint(latitude=10.300, longitude=123.927)
    )
    request = PlanRequest(
        origin=Endpoint(latitude=10.300, longitude=123.900),
        destination=destination,
        max_transfers=1 if transfer else 0,
        sort_by="cheapest",
        query_date=date(2026, 10, 21),
    )
    return plan_journeys(
        network,
        request,
        config={"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": False},
    )


def _band_rule(rule):
    return replace(
        rule,
        kind="distance_band",
        valid_from=date(2026, 9, 28),
        policy={
            "base_centavos": 1400,
            "base_distance_m": 4000,
            "increment_centavos": 200,
            "increment_distance_m": 1000,
            "rounding_centavos": 25,
            "max_distance_m": 50000,
        },
    )


def test_exact_fare_reaches_segments_totals_and_ranking():
    result = _plan(base_network())
    option = result.journey_options[0]
    ride = next(s for s in option["segments"] if s["mode"] == "ride")

    assert ride["fare"]["amount_centavos"] == 1300
    assert ride["fare"]["status"] == "exact"
    assert ride["fare"]["reason"] is None
    assert option["fare"]["per_leg"][0]["status"] == "exact"
    assert option["fare"]["total_centavos"] == 1300
    assert option["fare"]["status"] == "exact"
    assert result.ranking["applied"] == "cheapest"
    assert "cheapest" in option["labels"]


def test_approximate_transfer_total_does_not_claim_cheapest():
    network = base_network()
    network.fares[1] = _band_rule(network.fares[1])

    result = _plan(network, transfer=True)
    option = next(o for o in result.journey_options if o["transfers"] == 1)

    assert [fare["status"] for fare in option["fare"]["per_leg"]] == [
        "exact", "approximate",
    ]
    assert option["fare"]["total_centavos"] == 2700
    assert option["fare"]["total_is_complete"] is True
    assert option["fare"]["status"] == "approximate"
    assert result.ranking["applied"] == "fewest_transfers"
    assert "cheapest" not in option["labels"]


def test_unsupported_fractional_distance_has_no_journey_price():
    network = base_network()
    network.fares[0] = _band_rule(network.fares[0])
    pattern = network.patterns[0]
    network.patterns[0] = replace(
        pattern,
        stops=pattern.stops[:-1] + (
            replace(pattern.stops[-1], distance_along_m=4055),
        ),
        segments=pattern.segments[:-1] + (
            replace(pattern.segments[-1], distance_m=2055),
        ),
    )

    result = _plan(network)
    option = result.journey_options[0]
    ride = next(s for s in option["segments"] if s["mode"] == "ride")

    assert ride["distance_m"] == 4055
    assert ride["fare"]["amount_centavos"] is None
    assert ride["fare"]["status"] == "unavailable"
    assert "part of a distance band" in ride["fare"]["reason"]
    assert option["fare"]["total_centavos"] is None
    assert option["fare"]["total_is_complete"] is False
    assert option["fare"]["status"] == "unavailable"
    assert result.ranking["applied"] == "fewest_transfers"
    assert "cheapest" not in option["labels"]
