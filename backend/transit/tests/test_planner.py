"""
Planner algorithm tests (pure Python; no DB). Mirrors the acceptance matrix in
docs/ROUTING_ALGORITHM.md section 10.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from datetime import date

import pytest

from transit.planner import plan_journeys
from transit.planner.engine import (
    LIMITED,
    PlannerError,
    REASON_INSUFFICIENT,
    REASON_NO_JOURNEY,
    REASON_SAME_LOCATION,
    WITHIN,
)
from transit.planner.models import Endpoint, PatternData, PlanRequest
from transit.tests.planner_fixtures import base_network

ON = date(2026, 6, 1)
CFG = {"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": False}


def _req(o_lat, o_lon, d_lat, d_lon, **kw):
    return PlanRequest(
        origin=Endpoint(latitude=o_lat, longitude=o_lon),
        destination=Endpoint(latitude=d_lat, longitude=d_lon),
        query_date=ON, **kw,
    )


# 1. Direct ride when board precedes exit on a verified pattern.
def test_direct_ride_found():
    net = base_network()
    req = _req(10.300, 123.900, 10.300, 123.909)  # near S1 -> near S2
    res = plan_journeys(net, req, config=CFG)
    assert res.reason is None
    assert res.request_coverage_status == WITHIN
    assert len(res.journey_options) >= 1
    opt = res.journey_options[0]
    assert opt["transfers"] == 0
    rides = [s for s in opt["segments"] if s["mode"] == "ride"]
    assert len(rides) == 1
    assert rides[0]["route_code"] == "A1"
    assert rides[0]["direction"] == "outbound"


# 2. Exit precedes board on same directional pattern -> no reversed ride.
def test_no_reverse_direction_ride():
    net = base_network()
    # Ask S4 -> S1 (backwards along the only outbound pattern). No inbound exists.
    req = _req(10.300, 123.927, 10.300, 123.900)
    res = plan_journeys(net, req, config=CFG)
    assert res.journey_options == []
    assert res.reason == REASON_NO_JOURNEY


# 3. Two verified patterns connect via a valid walkable transfer.
def test_one_transfer_found():
    net = base_network()
    # S1 (A) -> S7 (B), requires transfer S3->S5.
    req = _req(10.300, 123.900, 10.3005, 123.936)
    res = plan_journeys(net, req, config=CFG)
    one_transfer = [o for o in res.journey_options if o["transfers"] == 1]
    assert one_transfer, "expected a one-transfer option"
    opt = one_transfer[0]
    modes = [s["mode"] for s in opt["segments"]]
    assert modes == ["walk", "ride", "transfer_walk", "ride", "walk"]
    rides = [s for s in opt["segments"] if s["mode"] == "ride"]
    assert rides[0]["route_code"] == "A1"
    assert rides[1]["route_code"] == "B2"


# 4. Three vehicle legs required -> no itinerary in MVP (max 1 transfer).
def test_more_than_one_transfer_excluded():
    net = base_network()
    # Add a third route C requiring a second transfer; ensure it's never returned
    # because max_transfers caps at 1.
    req = _req(10.300, 123.900, 10.3005, 123.936, max_transfers=1)
    res = plan_journeys(net, req, config=CFG)
    assert all(o["transfers"] <= 1 for o in res.journey_options)


# 5. Patterns cross but no authorized/walkable transfer -> reject transfer.
def test_no_transfer_without_connection():
    net = base_network()
    net.transfers = []  # remove the only transfer link
    req = _req(10.300, 123.900, 10.3005, 123.936)  # S1(A) -> S7(B)
    res = plan_journeys(net, req, config=CFG)
    # No direct ride spans A->B, and no transfer link exists.
    assert all(o["transfers"] == 0 for o in res.journey_options)
    assert not any(o["transfers"] == 1 for o in res.journey_options)
    # Specifically, S1->S7 should yield nothing.
    assert res.journey_options == []


# 6. Pattern is candidate/documented/needs_review -> excluded from trusted search.
@pytest.mark.parametrize("status", ["candidate", "documented", "needs_review"])
def test_unverified_pattern_excluded(status):
    net = base_network()
    net.patterns[0] = replace(net.patterns[0], status=status)
    req = _req(10.300, 123.900, 10.300, 123.909)  # needs pattern A
    res = plan_journeys(net, req, config=CFG)
    assert res.journey_options == []


# 6b. documented pattern INCLUDED when ALLOW_DOCUMENTED and warned.
def test_documented_included_when_enabled_with_warning():
    net = base_network()
    net.patterns[0] = replace(net.patterns[0], status="documented")
    req = _req(10.300, 123.900, 10.300, 123.909)
    res = plan_journeys(net, req, config={**CFG, "ALLOW_DOCUMENTED": True})
    assert len(res.journey_options) >= 1
    assert res.request_coverage_status == LIMITED
    assert any("not field-verified" in w.lower() or "historic" in w.lower() for w in res.warnings)


# 7. Historical fare rule superseded -> date-aware; here: expired => unknown fare.
def test_expired_fare_rule_yields_unknown():
    net = base_network()
    net.fares[0] = replace(net.fares[0], valid_until=date(2026, 1, 31))  # expired by ON
    req = _req(10.300, 123.900, 10.300, 123.909)
    res = plan_journeys(net, req, config=CFG)
    opt = res.journey_options[0]
    assert opt["fare"]["total_centavos"] is None
    assert opt["fare"]["total_is_complete"] is False
    assert opt["fare"]["per_leg"][0]["amount_centavos"] is None


# 8. Waiting estimate unavailable -> null and total duration incomplete.
def test_waiting_unknown_total_incomplete():
    net = base_network()
    req = _req(10.300, 123.900, 10.300, 123.909)
    res = plan_journeys(net, req, config=CFG)
    t = res.journey_options[0]["time"]
    assert t["waiting_seconds"] is None
    assert t["total_seconds"] is None
    assert t["total_is_complete"] is False
    assert t["riding_seconds"] == 300  # one segment, known


# 9. Two searches producing an equivalent path are deduplicated.
def test_deduplication():
    net = base_network()
    # Add a duplicate stop very close to S1 so two origin candidates map to the
    # same boarding occurrence/path.
    from transit.planner.models import StopData
    net.stops["S1b"] = StopData(id="S1b", name="Near One", latitude=10.3001,
                                longitude=123.9001, status="verified")
    req = _req(10.300, 123.900, 10.300, 123.909)
    res = plan_journeys(net, req, config=CFG)
    keys = {tuple((s["mode"], s.get("route_pattern_id")) for s in o["segments"])
            for o in res.journey_options}
    assert len(keys) == len(res.journey_options)  # no duplicates


# 10. Only one valid itinerary exists -> return exactly one, invent nothing.
def test_single_option_not_padded():
    net = base_network()
    req = _req(10.300, 123.900, 10.300, 123.909, limit=5)
    res = plan_journeys(net, req, config=CFG)
    assert len(res.journey_options) == 1


# 11 & 12. Return direction independent (reverse pattern absent).
def test_independent_return_fails_when_no_reverse():
    net = base_network()
    outbound = plan_journeys(net, _req(10.300, 123.900, 10.300, 123.927), config=CFG)
    assert outbound.journey_options  # A1 S1->S4 works outbound
    ret = plan_journeys(net, _req(10.300, 123.927, 10.300, 123.900), config=CFG)
    assert ret.journey_options == []  # no inbound pattern -> independent failure
    assert ret.reason == REASON_NO_JOURNEY


# 13. Unknown fare on one leg -> total unknown, not treated as free.
def test_unknown_fare_one_leg_total_unknown():
    net = base_network()
    # Route B gets no applicable fare: make its vehicle_class unmatched.
    net.routes["R-B"] = replace(net.routes["R-B"], vehicle_class="bus")
    req = _req(10.300, 123.900, 10.3005, 123.936)  # transfer A(jeepney)+B(bus)
    res = plan_journeys(net, req, config=CFG)
    one = [o for o in res.journey_options if o["transfers"] == 1][0]
    amounts = [leg["amount_centavos"] for leg in one["fare"]["per_leg"]]
    assert None in amounts  # B leg unknown
    assert one["fare"]["total_centavos"] is None
    assert one["fare"]["total_is_complete"] is False
    assert one["fare"]["known_subtotal_centavos"] == 1300  # A leg still known


# 14. Invalid/out-of-range coordinates rejected.
@pytest.mark.parametrize("lat,lon", [(91.0, 123.9), (-91.0, 123.9), (10.3, 181.0), (10.3, -181.0)])
def test_invalid_coordinates_rejected(lat, lon):
    net = base_network()
    with pytest.raises(PlannerError):
        plan_journeys(net, _req(lat, lon, 10.3, 123.91), config=CFG)


def test_nan_and_bool_coordinates_rejected():
    net = base_network()
    with pytest.raises(PlannerError):
        plan_journeys(net, _req(float("nan"), 123.9, 10.3, 123.91), config=CFG)
    with pytest.raises(PlannerError):
        plan_journeys(net, PlanRequest(
            origin=Endpoint(latitude=True, longitude=123.9),  # type: ignore[arg-type]
            destination=Endpoint(latitude=10.3, longitude=123.91), query_date=ON), config=CFG)


def test_invalid_sort_and_limits_rejected():
    net = base_network()
    with pytest.raises(PlannerError):
        plan_journeys(net, _req(10.3, 123.9, 10.3, 123.91, sort_by="bogus"), config=CFG)
    with pytest.raises(PlannerError):
        plan_journeys(net, _req(10.3, 123.9, 10.3, 123.91, limit=0), config=CFG)
    with pytest.raises(PlannerError):
        plan_journeys(net, _req(10.3, 123.9, 10.3, 123.91, max_transfers=2), config=CFG)


# 15. Same location -> same_location reason, no fabricated journey.
def test_same_location():
    net = base_network()
    res = plan_journeys(net, _req(10.300, 123.900, 10.3000, 123.9000), config=CFG)
    assert res.reason == REASON_SAME_LOCATION
    assert res.journey_options == []


# Empty / no eligible stop near endpoint.
def test_no_eligible_stop_near_endpoint():
    net = base_network()
    # Destination far from any stop (> radius).
    res = plan_journeys(net, _req(10.300, 123.900, 10.800, 124.400), config=CFG)
    assert res.journey_options == []
    assert res.reason == REASON_INSUFFICIENT


# Ranking fallback: cheapest requested but a fare unknown -> fewest_transfers.
def test_cheapest_fallback_discloses():
    net = base_network()
    net.routes["R-B"] = replace(net.routes["R-B"], vehicle_class="bus")  # B fare unknown
    req = _req(10.300, 123.900, 10.3005, 123.936, sort_by="cheapest")
    res = plan_journeys(net, req, config=CFG)
    assert res.ranking["requested"] == "cheapest"
    assert res.ranking["applied"] == "fewest_transfers"
    assert res.ranking["warning"]


# Direct fare computed correctly from verified flat rule.
def test_direct_fare_amount():
    net = base_network()
    res = plan_journeys(net, _req(10.300, 123.900, 10.300, 123.927), config=CFG)
    opt = res.journey_options[0]
    assert opt["fare"]["total_centavos"] == 1300
    assert opt["fare"]["total_is_complete"] is True


# Distance-band fare math.
def test_distance_band_fare():
    from transit.planner.fares import compute_leg_fare_centavos
    from transit.planner.models import FarePolicy
    rule = FarePolicy(id="x", vehicle_class="jeepney", route_id=None, pattern_id=None,
                      passenger_category="regular", currency="PHP", kind="distance_band",
                      policy={"base_centavos": 1300, "base_distance_m": 4000,
                              "increment_centavos": 180, "increment_distance_m": 1000},
                      valid_from=date(2026, 1, 1), valid_until=None, status="verified")
    assert compute_leg_fare_centavos(rule, 3000) == 1300          # within base
    assert compute_leg_fare_centavos(rule, 4000) == 1300          # exactly base
    assert compute_leg_fare_centavos(rule, 4001) == 1480          # 1 band over
    assert compute_leg_fare_centavos(rule, 6000) == 1300 + 2 * 180  # 2 bands


def test_shorter_ride_ranks_before_long_loop():
    from transit.planner.models import PatternData, PatternStopData, RouteData, SegmentData

    net = base_network()
    # A second direct route between the same stops that takes a 9 km loop.
    net.routes["R-L"] = RouteData(id="R-L", code="LOOP", name="Loop", vehicle_class="jeepney", operator=None)
    occ = (PatternStopData("L-o1", "S1", 0, 0, True, True), PatternStopData("L-o2", "S2", 1, 9000, True, True))
    net.patterns.insert(0, PatternData(
        id="P-L", route_id="R-L", direction="outbound", variant_key="loop", signboard=None,
        status="verified", verified_at=None, stops=occ,
        segments=(SegmentData("L-o1", "L-o2", 9000, 1800, "sourced_observation"),),
    ))
    res = plan_journeys(net, _req(10.300, 123.900, 10.300, 123.909), config=CFG)
    codes = [next(s["route_code"] for s in o["segments"] if s["mode"] == "ride") for o in res.journey_options]
    assert codes == ["A1", "LOOP"]
