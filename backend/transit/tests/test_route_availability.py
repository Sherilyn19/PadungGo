"""Availability flags, stable grouping and inactive-route safeguards."""
from copy import deepcopy
from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from django.core.exceptions import ValidationError
from django.test import Client

from transit.models import NetworkDataVersion, Route, RoutePattern
from transit.planner import loader, plan_journeys
from transit.planner.journey_types import Endpoint, PlanRequest
from transit.planner.ranking import rank_options
from transit.planner.responses import (
    REASON_NO_JOURNEY,
    empty_result,
    journey_result,
)
from transit.tests.db_fixtures import build_verified_network
from transit.tests.planner_fixtures import base_network


SORTS = ("fewest_transfers", "cheapest", "fastest", "least_walking")


def request(*, transfer=False, sort_by="fewest_transfers", limit=50):
    return PlanRequest(
        origin=Endpoint(latitude=10.300, longitude=123.900),
        destination=Endpoint(
            latitude=10.3005 if transfer else 10.300,
            longitude=123.936 if transfer else 123.927,
        ),
        max_transfers=1 if transfer else 0,
        sort_by=sort_by,
        limit=limit,
        query_date=date(2026, 10, 23),
    )


def plan(network, *, transfer=False):
    return plan_journeys(
        network,
        request(transfer=transfer),
        config={"STOP_SEARCH_RADIUS_M": 500, "ALLOW_DOCUMENTED": False},
    )


def rides(option):
    return [s for s in option["segments"] if s["mode"] == "ride"]


@pytest.mark.parametrize("code", ("01B", "14B", "12K", "22G"))
def test_scarce_flag_comes_from_record_not_code(code):
    network = base_network()
    network.routes["R-A"] = replace(
        network.routes["R-A"], code=code, service_availability="scarce"
    )
    options = plan(network).journey_options

    assert options
    for option in options:
        assert option["has_scarce_ride"] is True
        for ride in rides(option):
            assert ride["service_availability"] == "scarce"
            assert ride["waiting_seconds"] is None


@pytest.mark.parametrize("route_id", ("R-A", "R-B"))
def test_either_transfer_leg_makes_journey_scarce(route_id):
    network = base_network()
    network.routes[route_id] = replace(
        network.routes[route_id], service_availability="scarce"
    )
    options = [
        o for o in plan(network, transfer=True).journey_options
        if o["transfers"] == 1
    ]

    assert options
    for option in options:
        assert option["has_scarce_ride"] is True
        assert sorted(s["service_availability"] for s in rides(option)) == [
            "not_flagged", "scarce",
        ]


@pytest.mark.parametrize("code", ("14D", "17B", "17D", "12L"))
def test_unflagged_routes_keep_existing_fares(code):
    network = base_network()
    network.routes["R-A"] = replace(network.routes["R-A"], code=code)
    options = plan(network).journey_options

    assert options
    for option in options:
        assert option["has_scarce_ride"] is False
        assert option["fare"]["total_centavos"] == 1300
        assert all(
            ride["service_availability"] == "not_flagged"
            for ride in rides(option)
        )


def candidates(*, fallback=False, only_scarce=False):
    """Synthetic alternatives exercise ranking independently of route search."""
    template = plan(base_network()).journey_options[0]
    result = []
    for index, scarce in enumerate((True, False, True, False)):
        option = deepcopy(template)
        option["has_scarce_ride"] = scarce or only_scarce
        option["_dedup_key"] = (("fixture", str(index)),)
        option["_ride_m"] = 3000
        option["_walk_known_m"] = 0
        option["labels"] = []
        option["fare"].update(
            total_centavos=1000 if scarce else 2000,
            total_is_complete=not fallback,
            status="unavailable" if fallback else "exact",
        )
        option["time"].update(
            total_seconds=100 if scarce else 200,
            total_is_complete=not fallback,
        )
        result.append(option)
    return result


@pytest.mark.parametrize("sort_by", SORTS)
@pytest.mark.parametrize("fallback", (False, True))
@pytest.mark.parametrize("limit", (1, 3, 4))
def test_stable_scarcity_grouping_precedes_limit(sort_by, fallback, limit):
    original = candidates(fallback=fallback)
    ranked, expected_ranking = rank_options(deepcopy(original), sort_by)
    expected = (
        [o for o in ranked if not o["has_scarce_ride"]]
        + [o for o in ranked if o["has_scarce_ride"]]
    )[:limit]

    result = journey_result(
        deepcopy(original),
        request(sort_by=sort_by, limit=limit),
        allow_documented=False,
        response_prefix="opt",
    )

    assert [
        (o["has_scarce_ride"], o["fare"]["total_centavos"])
        for o in result.journey_options
    ] == [
        (o["has_scarce_ride"], o["fare"]["total_centavos"])
        for o in expected
    ]
    assert [o["id"] for o in result.journey_options] == [
        f"opt-{index + 1}" for index in range(len(expected))
    ]
    assert result.ranking == {**expected_ranking, "scarce_last": True}

    # Distinguish tied alternatives to check their order, not just their flags.
    for index, option in enumerate(original):
        option["test_identity"] = index
    ordered = journey_result(
        deepcopy(original),
        request(sort_by=sort_by, limit=4),
        allow_documented=False,
        response_prefix="opt",
    )
    assert [o["test_identity"] for o in ordered.journey_options] == [1, 3, 0, 2]


def test_only_scarce_options_are_returned():
    result = journey_result(
        candidates(only_scarce=True),
        request(),
        allow_documented=False,
        response_prefix="opt",
    )
    assert len(result.journey_options) == 4
    assert all(o["has_scarce_ride"] for o in result.journey_options)


def test_empty_result_has_scarcity_policy():
    result = empty_result(request(), REASON_NO_JOURNEY)
    assert result.journey_options == []
    assert result.ranking["scarce_last"] is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    "inactive_route,transfer",
    (("A", False), ("A", True), ("B", True)),
)
def test_inactive_routes_are_not_loaded_or_suggested(inactive_route, transfer):
    fixture = build_verified_network()
    route = fixture["routes"][inactive_route]
    route.active = False
    route.save()

    network = loader.load_network(use_cache=False)
    assert str(route.pk) not in network.routes
    assert all(p.route_id != str(route.pk) for p in network.patterns)
    result = plan(network, transfer=transfer)
    assert not any(
        s["route_id"] == str(route.pk)
        for option in result.journey_options
        for s in rides(option)
    )
    if transfer:
        assert not any(o["transfers"] == 1 for o in result.journey_options)
    else:
        assert result.journey_options == []

    # Exclusion does not delete the original data.
    assert Route.objects.filter(pk=route.pk).exists()
    assert RoutePattern.objects.filter(route=route).exists()

    client = Client()
    assert client.get(f"/api/v1/routes/{route.pk}").status_code == 404
    response = client.get("/api/v1/routes", {"limit": 50})
    assert response.status_code == 200
    assert str(route.pk) not in {
        row["id"] for row in response.json()["results"]
    }


@pytest.mark.django_db
def test_duplicate_codes_are_flagged_per_record():
    fixture = build_verified_network()
    first, second = fixture["routes"]["A"], fixture["routes"]["B"]
    first.code = second.code = "SAME"
    first.service_availability = "scarce"
    first.save()
    second.save()

    network = loader.load_network(use_cache=False)
    assert network.routes[str(first.pk)].service_availability == "scarce"
    assert network.routes[str(second.pk)].service_availability == "not_flagged"


@pytest.mark.django_db
def test_invalid_availability_is_rejected_by_model_validation():
    route = Route(
        code="TEST",
        vehicle_class="jeepney",
        service_availability="frequent",
    )
    with pytest.raises(ValidationError) as error:
        route.full_clean()
    assert "service_availability" in error.value.message_dict


@pytest.mark.django_db
def test_admin_style_flag_save_refreshes_cache_date_and_api(monkeypatch):
    fixture = build_verified_network()
    route = fixture["routes"]["A"]
    original_network = loader.load_network()
    assert original_network.routes[str(route.pk)].service_availability == "not_flagged"

    marker = NetworkDataVersion.objects.get(
        pk=NetworkDataVersion.SINGLETON_ID
    )
    before = marker.version
    edited_at = datetime(2026, 10, 23, 17, tzinfo=timezone.utc)
    monkeypatch.setattr(loader.timezone, "now", lambda: edited_at)

    route.service_availability = "scarce"
    route.save()
    marker.refresh_from_db()

    assert marker.version == before + 1
    assert marker.updated_at == edited_at
    assert loader.load_network().routes[str(route.pk)].service_availability == "scarce"

    response = Client().post(
        "/api/v1/journeys/plan",
        data={
            "origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.300, "longitude": 123.927},
        },
        content_type="application/json",
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_updated_on"] == "2026-10-24"
    assert payload["ranking"]["scarce_last"] is True
    assert payload["journey_options"]
    for option in payload["journey_options"]:
        assert option["has_scarce_ride"] is True
        assert all(
            ride["service_availability"] == "scarce"
            for ride in rides(option)
        )