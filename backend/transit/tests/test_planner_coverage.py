"""When no trip is found, say why: which end has no stop, how far the nearest one is,
and whether the other direction works. Synthetic fixtures only."""
from __future__ import annotations

from dataclasses import replace
from datetime import date

from transit.planner import plan_journeys
from transit.planner.journey_types import Endpoint, PlanRequest
from transit.tests.planner_fixtures import base_network

CFG = {"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": False}


def plan(origin, destination, net=None, **kw):
    req = PlanRequest(origin=Endpoint(*origin), destination=Endpoint(*destination), limit=50,
                      query_date=date(2026, 10, 23), **kw)
    return plan_journeys(net or base_network(), req, config=CFG).to_dict()


S1 = (10.300, 123.900)       # on route A, west end
S4 = (10.300, 123.927)       # on route A, east end
FAR_EAST = (10.300, 124.100)    # about 18 km past the last stop
FAR_WEST = (10.300, 123.700)


def test_a_found_trip_has_no_coverage_note():
    result = plan(S1, S4)
    assert result["journey_options"] and result["coverage"] is None


def test_destination_with_no_stop_is_named_with_its_distance():
    result = plan(S1, FAR_EAST)
    assert result["reason"] == "insufficient_verified_data"
    cov = result["coverage"]
    assert cov["origin_has_stop"] is True and cov["destination_has_stop"] is False
    assert cov["search_radius_m"] == 500
    # The nearest alighting stop is about 18 km away (0.164 degrees of longitude); distances are rounded to 100 m.
    assert 17_500 < cov["nearest_destination_stop_m"] < 18_500 and cov["nearest_destination_stop_m"] % 100 == 0
    assert cov["nearest_origin_stop_m"] <= 500 and cov["reverse_has_trips"] is None


def test_origin_with_no_stop_is_named():
    cov = plan(FAR_WEST, S4)["coverage"]
    assert cov["origin_has_stop"] is False and cov["destination_has_stop"] is True
    assert cov["nearest_origin_stop_m"] > 15_000


def test_both_ends_without_stops():
    cov = plan(FAR_WEST, FAR_EAST)["coverage"]
    assert cov["origin_has_stop"] is False and cov["destination_has_stop"] is False


def test_empty_network_reports_unknown_distances_not_zero():
    net = base_network()
    net.stops.clear()
    cov = plan(S1, S4, net)["coverage"]
    assert cov["nearest_origin_stop_m"] is None and cov["nearest_destination_stop_m"] is None


def test_stops_the_status_gate_excludes_are_not_counted():
    net = base_network()
    net.stops = {k: replace(v, status="candidate") for k, v in net.stops.items()}
    cov = plan(S1, S4, net)["coverage"]
    assert cov["nearest_origin_stop_m"] is None and cov["origin_has_stop"] is False


def test_one_way_service_says_the_other_direction_works():
    # Route A only runs west to east: east to west has stops at both ends but no trip.
    result = plan(S4, S1)
    assert result["reason"] == "no_journey_within_mvp_limits"
    cov = result["coverage"]
    assert cov["origin_has_stop"] and cov["destination_has_stop"]
    assert cov["reverse_has_trips"] is True


def test_no_trip_in_either_direction_is_false_not_missing():
    net = base_network()
    net.transfers = []              # routes cannot be linked ...
    result = plan((10.300, 123.900), (10.3005, 123.936), net, max_transfers=0)   # ... and no direct ride exists
    assert result["reason"] == "no_journey_within_mvp_limits"
    assert result["coverage"]["reverse_has_trips"] is False


def test_same_location_has_no_coverage_note():
    assert plan(S1, S1)["coverage"] is None
