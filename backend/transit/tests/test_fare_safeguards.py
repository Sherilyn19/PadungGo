"""Fare safeguards: only evidence-backed, route-scoped verified rules produce a price."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from django.core.exceptions import ValidationError

from transit.models import DataSource, FareRule, RecordEvidence, Route, RoutePattern
from transit.planner import plan_journeys
from transit.planner.fares import resolve_fare_rule
from transit.planner.journey_types import Endpoint, FarePolicy, PlanRequest
from transit.tests.planner_fixtures import base_network

NOW = datetime(2026, 10, 20, tzinfo=timezone.utc)
BAND_2026 = {"base_centavos": 1400, "base_distance_m": 4000,
             "increment_centavos": 200, "increment_distance_m": 1000}


# --- Planner: which rules may price a leg (no database) ----------------------

def _policy(fare_id, *, route_id="R-A", status="verified", amount=1300,
            valid_from=date(2026, 1, 1), valid_until=None, vehicle_class="jeepney"):
    return FarePolicy(
        id=fare_id, vehicle_class=vehicle_class, route_id=route_id, pattern_id=None,
        passenger_category="regular", currency="PHP", kind="flat",
        policy={"amount_centavos": amount}, valid_from=valid_from,
        valid_until=valid_until, status=status,
    )


def _resolve(net, on=date(2026, 10, 20), route_id="R-A"):
    return resolve_fare_rule(net, route=net.routes[route_id], pattern_id="P-A-out",
                             passenger_category="regular", on=on)


def test_route_scoped_verified_rule_applies():
    net = base_network()
    net.fares = [_policy("F-route")]
    assert _resolve(net).id == "F-route"


def test_class_wide_verified_rule_is_never_applied():
    net = base_network()
    net.fares = [_policy("F-class", route_id=None)]
    assert _resolve(net) is None


@pytest.mark.parametrize("status", ["documented", "candidate", "needs_review"])
def test_unverified_rules_never_price_a_leg(status):
    net = base_network()
    net.fares = [_policy("F-x", status=status)]
    assert _resolve(net) is None


def test_rule_stops_applying_when_route_vehicle_class_changes():
    net = base_network()
    net.fares = [_policy("F-route")]
    net.routes["R-A"] = replace(net.routes["R-A"], vehicle_class="mixed")
    assert _resolve(net) is None


def test_fare_change_date_boundary():
    net = base_network()
    net.fares = [
        _policy("F-old", amount=1300, valid_until=date(2026, 9, 27)),
        _policy("F-new", amount=1400, valid_from=date(2026, 9, 28)),
    ]
    assert _resolve(net, on=date(2026, 9, 27)).id == "F-old"
    assert _resolve(net, on=date(2026, 9, 28)).id == "F-new"
    assert _resolve(net, on=date(2026, 12, 31)).id == "F-new"
    assert _resolve(net, on=date(2025, 12, 31)) is None  # before any rule


def test_overlapping_rules_without_end_date_give_unknown_fare():
    # An old rule that was never end-dated must not silently compete with the new one.
    net = base_network()
    net.fares = [_policy("F-old", amount=1300), _policy("F-new", amount=1400,
                                                        valid_from=date(2026, 9, 28))]
    assert _resolve(net, on=date(2026, 9, 27)).id == "F-old"
    assert _resolve(net, on=date(2026, 9, 28)) is None


def test_mixed_fleet_leg_shows_unknown_fare_with_reason():
    net = base_network()
    net.routes["R-B"] = replace(net.routes["R-B"], vehicle_class="mixed")
    req = PlanRequest(origin=Endpoint(latitude=10.300, longitude=123.900),
                      destination=Endpoint(latitude=10.3005, longitude=123.936),
                      max_transfers=1, limit=5, sort_by="fewest_transfers",
                      query_date=date(2026, 6, 1))
    res = plan_journeys(net, req, config={"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": False})
    option = next(o for o in res.journey_options if o["transfers"] == 1)
    route_a_leg, route_b_leg = option["fare"]["per_leg"]
    assert route_a_leg["amount_centavos"] == 1300
    assert route_b_leg["amount_centavos"] is None
    assert "traditional and modern" in route_b_leg["assumptions"]
    assert option["fare"]["total_centavos"] is None


# --- Model: verification is rejected without its basis ----------------------

@pytest.fixture
def service(db):
    source = DataSource.objects.create(title="Fare guide (test)", collected_at=NOW)
    route = Route.objects.create(code="42D", vehicle_class="jeepney")
    verified = RoutePattern.objects.create(route=route, variant_key="v", direction="outbound",
                                           status="verified")
    documented = RoutePattern.objects.create(route=route, variant_key="w", direction="inbound",
                                             status="documented")
    return {"source": source, "route": route, "verified": verified, "documented": documented}


def _rule(service, **fields):
    values = {"vehicle_class": "jeepney", "route": service["route"], "kind": "distance_band",
              "policy": BAND_2026, "valid_from": date(2026, 9, 28), "status": "documented",
              "source": service["source"]}
    values.update(fields)
    return FareRule(**values)


def _add_evidence(service, rule, status="verified"):
    RecordEvidence.objects.create(fare_rule=rule, source=service["source"], reviewed_at=NOW,
                                  reviewer="tester", status=status)


def _verify(rule):
    rule.status = "verified"
    rule.full_clean()


def test_documented_rule_needs_no_route_so_it_can_be_recorded_for_review(service):
    _rule(service, route=None).full_clean()


def test_rule_with_route_verified_pattern_and_evidence_can_be_verified(service):
    rule = _rule(service)
    rule.save()
    _add_evidence(service, rule)
    _verify(rule)


def test_pattern_scoped_rule_on_verified_pattern_can_be_verified(service):
    rule = _rule(service, route=None, pattern=service["verified"])
    rule.save()
    _add_evidence(service, rule)
    _verify(rule)


def test_verification_rejected_without_route_or_pattern(service):
    rule = _rule(service, route=None)
    with pytest.raises(ValidationError, match="must name the route or route pattern"):
        _verify(rule)


def test_verification_rejected_when_vehicle_class_differs_from_route(service):
    rule = _rule(service, vehicle_class="modern_puv")
    with pytest.raises(ValidationError, match="recorded as 'jeepney'"):
        _verify(rule)


def test_verification_rejected_when_route_fleet_not_confirmed(service):
    service["verified"].status = "documented"
    service["verified"].save()
    rule = _rule(service)
    with pytest.raises(ValidationError, match="none of its patterns is verified"):
        _verify(rule)


def test_verification_rejected_for_unverified_pattern(service):
    rule = _rule(service, route=None, pattern=service["documented"])
    with pytest.raises(ValidationError, match="this pattern is verified"):
        _verify(rule)


@pytest.mark.parametrize("evidence_status", [None, "documented", "candidate"])
def test_verification_rejected_without_verified_evidence(service, evidence_status):
    rule = _rule(service)
    rule.save()
    if evidence_status:
        _add_evidence(service, rule, status=evidence_status)
    with pytest.raises(ValidationError, match="needs verified supporting evidence"):
        _verify(rule)


def test_mixed_fleet_fare_rule_rejected_at_any_status(service):
    with pytest.raises(ValidationError, match="one vehicle type"):
        _rule(service, vehicle_class="mixed").full_clean()


# --- Loader: a status set outside Admin still cannot produce a price ----------

def test_loader_ignores_verified_rule_without_verified_evidence(service):
    from transit.planner.loader import invalidate_network_cache, load_network

    rule = _rule(service)
    rule.save()
    FareRule.objects.filter(pk=rule.pk).update(status="verified")  # bypasses clean()
    invalidate_network_cache()
    assert load_network(allow_documented=True).fares == []

    _add_evidence(service, rule)  # the evidence save also refreshes the cache
    assert [f.id for f in load_network(allow_documented=True).fares] == [str(rule.pk)]
