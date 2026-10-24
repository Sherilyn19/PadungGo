"""When no trip is found, say why: which end has no stop, how far the nearest one is,
and whether the other direction works. Synthetic fixtures only."""
from __future__ import annotations

from dataclasses import replace

import pytest
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


# --- Loop rides: do not offer a long ride that ends where it began ----------------

from transit.planner.journey_types import PatternData, PatternStopData, RouteData, SegmentData, StopData
from transit.planner.search import is_loop_ride


def _loop_network(end_gap_deg):
    """One route: east 2.2 km, north 1.1 km, then back to near the start (end_gap_deg east of it)."""
    net = base_network()
    net.patterns, net.transfers, net.fares, net.stops, net.routes = [], [], [], {}, {}
    pts = [("L1", 10.300, 123.900, 0), ("L2", 10.300, 123.920, 2200), ("L3", 10.310, 123.920, 3300),
           ("L4", 10.300, 123.900 + end_gap_deg, 5400)]
    for sid, la, lo, _ in pts:
        net.stops[sid] = StopData(id=sid, name=sid, latitude=la, longitude=lo, status="verified")
    net.routes["R-L"] = RouteData(id="R-L", code="77L", name="Loop", vehicle_class="jeepney", operator=None)
    stops = tuple(PatternStopData(id=f"o{i}", stop_id=sid, sequence=i, distance_along_m=d, can_board=True, can_alight=True)
                  for i, (sid, _, _, d) in enumerate(pts))
    segs = tuple(SegmentData(from_occurrence_id=a.id, to_occurrence_id=b.id, distance_m=b.distance_along_m - a.distance_along_m,
                             riding_seconds=60, estimate_basis="sourced_observation")
                 for a, b in zip(stops, stops[1:]))
    net.patterns.append(PatternData(id="P-L", route_id="R-L", direction="loop", variant_key="v", signboard=None,
                                    status="verified", verified_at="2026-01-01", stops=stops, segments=segs,
                                    evidence_source_ids=("src-1",), has_verified_evidence=True))
    return net


def test_a_ride_that_returns_to_where_it_began_is_not_offered():
    net = _loop_network(0.0005)                       # last stop about 55 m from the first
    result = plan((10.300, 123.9003), (10.300, 123.9007), net)     # both ends are next to L1 and L4
    assert result["journey_options"] == [] and result["reason"] == "no_journey_within_mvp_limits"


def test_the_same_route_still_serves_real_trips():
    result = plan((10.300, 123.900), (10.300, 123.920), _loop_network(0.0005))   # L1 to L2: 2.2 km ride, 2.2 km apart
    assert [o["segments"][1]["route_code"] for o in result["journey_options"]] == ["77L"]


def _pair(ride_m, gap_m_lon):
    net = _loop_network(gap_m_lon)
    a, b = net.patterns[0].stops[0], net.patterns[0].stops[3]
    return net, a, PatternStopData(id=b.id, stop_id=b.stop_id, sequence=b.sequence, distance_along_m=ride_m,
                                   can_board=True, can_alight=True)


@pytest.mark.parametrize("ride_m,gap_deg,expected", [
    (5400, 0.0005, True),     # 55 m apart, 5.4 km ride: a loop
    (2900, 0.0005, False),    # ride under 3 km: allowed
    (5400, 0.0100, False),    # 1.1 km apart (not a short walk): allowed
    (3100, 0.0080, True),     # about 890 m apart and a 3.1 km ride is more than 3x that: a loop
])
def test_loop_ride_limits(ride_m, gap_deg, expected):
    net, a, b = _pair(ride_m, gap_deg)
    assert is_loop_ride(net, a, b) is expected


def test_unknown_stops_are_never_treated_as_a_loop():
    net, a, b = _pair(9000, 0.0005)
    net.stops.pop(b.stop_id)
    assert is_loop_ride(net, a, b) is False
