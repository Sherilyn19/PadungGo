"""Exercise fare classification through the planner using synthetic services."""
from dataclasses import replace
from datetime import date

from transit.planner import plan_journeys
from transit.planner.journey_types import Endpoint, PlanRequest
from transit.tests.planner_fixtures import base_network

import json
import pytest
from transit.planner import assembly


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

@pytest.mark.parametrize("transfer", (False, True))
@pytest.mark.parametrize("fare_kind", ("flat", "distance_band", "missing"))
def test_guide_estimates_preserve_existing_planner_output(
    monkeypatch, transfer, fare_kind
):
    network = base_network()
    if fare_kind == "distance_band":
        network.fares = [_band_rule(rule) for rule in network.fares]
    elif fare_kind == "missing":
        network.fares.clear()

    # Reconstruct the pre-change assembly output by removing only the new field.
    original_ride_segment = assembly._ride_segment

    def without_guide_estimate(context, leg):
        segment = original_ride_segment(context, leg)
        segment.pop("guide_fare_estimate")
        return segment

    with monkeypatch.context() as patch:
        patch.setattr(assembly, "_ride_segment", without_guide_estimate)
        baseline = _plan(network, transfer=transfer)

    actual = _plan(network, transfer=transfer)
    assert actual.journey_options
    if transfer:
        assert any(o["transfers"] == 1 for o in actual.journey_options)

    for option in actual.journey_options:
        for segment in option["segments"]:
            if segment["mode"] != "ride":
                assert "guide_fare_estimate" not in segment
                continue

            estimate = segment.pop("guide_fare_estimate")
            assert estimate["status"] == "available"
            assert estimate["known_vehicle_type"] is None
            assert set(estimate) == {
                "status",
                "reason",
                "guide_effective_date",
                "chargeable_km",
                "known_vehicle_type",
                "amounts_centavos",
            }

    # Compare serialized output, including all fare metadata and totals.
    # Existing literal-value tests above independently anchor fare correctness.
    assert json.dumps(actual.journey_options, sort_keys=True) == json.dumps(
        baseline.journey_options, sort_keys=True
    )
    assert actual.ranking == baseline.ranking


@pytest.mark.parametrize("vehicle_class", ("jeepney", "modern_puv", "mixed"))
def test_documented_routes_receive_estimates_without_vehicle_classification(
    vehicle_class,
):
    network = base_network()
    network.fares.clear()
    network.routes = {
        route_id: replace(route, vehicle_class=vehicle_class)
        for route_id, route in network.routes.items()
    }
    network.patterns = [
        replace(
            pattern,
            status="documented",
            verified_at=None,
            has_verified_evidence=False,
        )
        for pattern in network.patterns
    ]
    request = PlanRequest(
        origin=Endpoint(latitude=10.300, longitude=123.900),
        destination=Endpoint(latitude=10.300, longitude=123.927),
        max_transfers=0,
        query_date=date(2026, 10, 21),
    )
    result = plan_journeys(
        network,
        request,
        config={"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": True},
    )

    assert result.journey_options
    option = result.journey_options[0]
    ride = next(s for s in option["segments"] if s["mode"] == "ride")

    assert ride["verification_status"] == "documented"
    assert ride["guide_fare_estimate"] == {
        "status": "available",
        "reason": None,
        "guide_effective_date": "2026-09-28",
        "chargeable_km": 3,
        "known_vehicle_type": None,
        "amounts_centavos": {
            "traditional": {"regular": 1400, "discounted": 1125},
            "modern": {"regular": 1700, "discounted": 1350},
        },
    }
    assert ride["fare"]["status"] == "unavailable"
    assert option["fare"]["total_centavos"] is None


def test_transfer_bus_has_no_guide_estimate_or_fabricated_total():
    network = base_network()
    network.routes["R-B"] = replace(
        network.routes["R-B"], vehicle_class="bus"
    )
    result = _plan(network, transfer=True)
    option = next(o for o in result.journey_options if o["transfers"] == 1)
    rides = [s for s in option["segments"] if s["mode"] == "ride"]

    assert len(rides) == 2
    assert rides[0]["guide_fare_estimate"]["status"] == "available"
    assert rides[1]["guide_fare_estimate"] == {
        "status": "unavailable",
        "reason": "not_puj",
        "guide_effective_date": "2026-09-28",
        "chargeable_km": None,
        "known_vehicle_type": None,
        "amounts_centavos": None,
    }
    assert option["fare"]["total_centavos"] is None
    assert option["fare"]["total_is_complete"] is False