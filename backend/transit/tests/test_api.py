"""API endpoint tests (DRF, SQLite lite mode)."""
from __future__ import annotations

import json

import pytest
from django.test import Client

from transit.models import Location
from transit.tests.db_fixtures import build_verified_network

pytestmark = pytest.mark.django_db


@pytest.fixture
def net():
    return build_verified_network()


@pytest.fixture
def client():
    return Client()


def _post_plan(client, body):
    return client.post("/api/v1/journeys/plan", data=json.dumps(body),
                       content_type="application/json")


# --- Read endpoints --------------------------------------------------------


def test_locations_search(client, net):
    Location.objects.create(name="Ayala Center Cebu", kind="mall",
                            latitude=10.3177, longitude=123.9057, status="verified")
    Location.objects.create(name="SM City Cebu", kind="mall",
                            latitude=10.3114, longitude=123.9183, status="verified")
    resp = client.get("/api/v1/locations", {"q": "ayala"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["results"]) == 1
    assert body["results"][0]["name"] == "Ayala Center Cebu"
    assert "latitude" in body["results"][0] and "longitude" in body["results"][0]


def test_routes_list(client, net):
    resp = client.get("/api/v1/routes")
    assert resp.status_code == 200
    codes = {r["code"] for r in resp.json()["results"]}
    assert codes == {"A1", "B2"}
    a1 = next(r for r in resp.json()["results"] if r["code"] == "A1")
    assert a1["patterns"][0]["direction"] == "outbound"


def test_route_detail_ok(client, net):
    route_id = str(net["routes"]["A"].id)
    resp = client.get(f"/api/v1/routes/{route_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "A1"
    stops = body["patterns"][0]["stops"]
    assert [s["sequence"] for s in stops] == [0, 1, 2, 3]
    assert stops[0]["stop_name"] == "Stop One"
    # private reviewer notes not exposed
    assert "reviewer" not in json.dumps(body)


def test_route_detail_unknown_404(client, net):
    resp = client.get("/api/v1/routes/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_route_detail_malformed_id_404(client, net):
    resp = client.get("/api/v1/routes/not-a-uuid")
    assert resp.status_code == 404


# --- Journey plan ----------------------------------------------------------


def test_plan_direct(client, net):
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.300, "longitude": 123.909}}
    resp = _post_plan(client, body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["reason"] is None
    assert len(data["journey_options"]) >= 1
    opt = data["journey_options"][0]
    assert opt["transfers"] == 0
    assert opt["fare"]["total_centavos"] == 1300
    assert opt["id"].startswith("opt-")


def test_plan_one_transfer(client, net):
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.3005, "longitude": 123.936}}
    data = _post_plan(client, body).json()
    assert any(o["transfers"] == 1 for o in data["journey_options"])


def test_plan_by_location_id(client, net):
    loc = Location.objects.create(name="Near One", kind="place",
                                  latitude=10.300, longitude=123.900, status="verified")
    body = {"origin": {"location_id": str(loc.id)},
            "destination": {"latitude": 10.300, "longitude": 123.909}}
    resp = _post_plan(client, body)
    assert resp.status_code == 200
    assert resp.json()["journey_options"]


def test_plan_unknown_location_id_400(client, net):
    body = {"origin": {"location_id": "00000000-0000-0000-0000-000000000000"},
            "destination": {"latitude": 10.300, "longitude": 123.909}}
    resp = _post_plan(client, body)
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_request"


def test_plan_ambiguous_endpoint_400(client, net):
    body = {"origin": {"location_id": "x", "latitude": 10.3, "longitude": 123.9},
            "destination": {"latitude": 10.300, "longitude": 123.909}}
    resp = _post_plan(client, body)
    assert resp.status_code == 400


def test_plan_invalid_coordinates_400(client, net):
    body = {"origin": {"latitude": 999, "longitude": 123.9},
            "destination": {"latitude": 10.300, "longitude": 123.909}}
    resp = _post_plan(client, body)
    assert resp.status_code == 400


def test_plan_unknown_field_400(client, net):
    body = {"origin": {"latitude": 10.3, "longitude": 123.9},
            "destination": {"latitude": 10.300, "longitude": 123.909},
            "bogus": 1}
    resp = _post_plan(client, body)
    assert resp.status_code == 400


def test_plan_empty_result_outside_coverage(client, net):
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 11.000, "longitude": 124.500}}
    data = _post_plan(client, body).json()
    assert data["journey_options"] == []
    assert data["reason"] in ("insufficient_verified_data", "no_journey_within_mvp_limits")


def test_plan_same_location(client, net):
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.300, "longitude": 123.900}}
    data = _post_plan(client, body).json()
    assert data["reason"] == "same_location"
    assert data["journey_options"] == []


def test_independent_return_differs(client, net):
    # Outbound S1 -> S4 works; return S4 -> S1 has no inbound pattern -> empty.
    out = _post_plan(client, {"origin": {"latitude": 10.300, "longitude": 123.900},
                              "destination": {"latitude": 10.300, "longitude": 123.927}}).json()
    assert out["journey_options"]
    ret = _post_plan(client, {"origin": {"latitude": 10.300, "longitude": 123.927},
                              "destination": {"latitude": 10.300, "longitude": 123.900}}).json()
    assert ret["journey_options"] == []


def test_plan_fare_unknown_total_incomplete(client, net):
    # No fare for bus; make route B a bus so the transfer leg fare is unknown.
    net["routes"]["B"].vehicle_class = "bus"
    net["routes"]["B"].save()
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.3005, "longitude": 123.936}}
    data = _post_plan(client, body).json()
    transfer_opts = [o for o in data["journey_options"] if o["transfers"] == 1]
    assert transfer_opts
    assert transfer_opts[0]["fare"]["total_is_complete"] is False
    assert transfer_opts[0]["fare"]["total_centavos"] is None


def test_plan_ignores_documented_fare_rules(client, net):
    # Announced-but-unconfirmed fares are stored as "documented" for review;
    # they must never be shown to commuters as a price.
    from transit.models import FareRule

    FareRule.objects.update(status="documented")
    body = {"origin": {"latitude": 10.300, "longitude": 123.900},
            "destination": {"latitude": 10.300, "longitude": 123.927}}
    option = _post_plan(client, body).json()["journey_options"][0]
    assert option["fare"]["total_centavos"] is None
    assert option["fare"]["per_leg"][0]["rule_id"] is None
    assert (
        "Total fare unavailable: at least one ride has no supported fare calculation."
        in option["warnings"]
    )

@pytest.mark.parametrize(
    "destination,expected_km",
    (
        ({"latitude": 10.300, "longitude": 123.927}, [3]),
        ({"latitude": 10.3005, "longitude": 123.936}, [2, 2]),
    ),
)
def test_plan_guide_estimate_contract(
    client, net, monkeypatch, destination, expected_km
):
    from datetime import date

    from transit.api import views

    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 10, 22)

    # The endpoint uses today's date; pin it after the guide takes effect.
    monkeypatch.setattr(views, "date", FixedDate)

    response = _post_plan(client, {
        "origin": {"latitude": 10.300, "longitude": 123.900},
        "destination": destination,
        "max_transfers": len(expected_km) - 1,
    })

    assert response.status_code == 200
    options = [
        option
        for option in response.json()["journey_options"]
        if option["transfers"] == len(expected_km) - 1
    ]
    assert options

    option = options[0]
    rides = [s for s in option["segments"] if s["mode"] == "ride"]
    assert [ride["distance_m"] for ride in rides] == [
        km * 1000 for km in expected_km
    ]

    for ride, km in zip(rides, expected_km):
        assert ride["guide_fare_estimate"] == {
            "status": "available",
            "reason": None,
            "guide_effective_date": "2026-09-28",
            "chargeable_km": km,
            "known_vehicle_type": None,
            "amounts_centavos": {
                "traditional": {"regular": 1400, "discounted": 1125},
                "modern": {"regular": 1700, "discounted": 1350},
            },
        }
        # The fixture's verified fare keeps its own amount and evidence.
        assert ride["fare"]["amount_centavos"] == 1300
        assert ride["fare"]["status"] == "exact"
        assert ride["fare"]["passenger_category"] == "regular"
        assert ride["fare"]["rule_id"] is not None
        assert ride["fare"]["source_ids"]

    assert option["fare"]["total_centavos"] == (
        1300 if len(expected_km) == 1 else 2600
    )
    assert option["fare"]["status"] == "exact"
    assert option["fare"]["total_is_complete"] is True

    for segment in option["segments"]:
        if segment["mode"] != "ride":
            assert "guide_fare_estimate" not in segment

@pytest.mark.parametrize(
    "utc_hour,expected_date",
    (
        (15, "2026-10-17"),
        (17, "2026-10-18"),
    ),
)
def test_plan_data_updated_on_uses_manila_date(
    client, net, utc_hour, expected_date
):
    from datetime import datetime, timezone

    from transit.models import NetworkDataVersion

    row, _ = NetworkDataVersion.objects.get_or_create(
        pk=NetworkDataVersion.SINGLETON_ID
    )
    timestamp = datetime(2026, 10, 17, utc_hour, tzinfo=timezone.utc)
    NetworkDataVersion.objects.filter(pk=row.pk).update(
        updated_at=timestamp
    )
    row.refresh_from_db()
    version_before = row.version

    response = _post_plan(client, {
        "origin": {"latitude": 10.300, "longitude": 123.900},
        "destination": {"latitude": 10.300, "longitude": 123.927},
    })

    assert response.status_code == 200
    assert response.json()["data_updated_on"] == expected_date
    row.refresh_from_db()
    assert row.updated_at == timestamp
    assert row.version == version_before


def test_plan_data_updated_on_missing_row_preserves_other_fields(client, net):
    from datetime import datetime, timezone

    from transit.models import NetworkDataVersion

    body = {
        "origin": {"latitude": 10.300, "longitude": 123.900},
        "destination": {"latitude": 10.300, "longitude": 123.927},
    }
    row, _ = NetworkDataVersion.objects.get_or_create(
        pk=NetworkDataVersion.SINGLETON_ID
    )
    NetworkDataVersion.objects.filter(pk=row.pk).update(
        updated_at=datetime(2026, 10, 17, 17, tzinfo=timezone.utc)
    )

    present_response = _post_plan(client, body)
    assert present_response.status_code == 200
    present = present_response.json()
    assert present.pop("data_updated_on") == "2026-10-18"
    assert present["journey_options"]

    # These are isolated test records, not production data.
    NetworkDataVersion.objects.all().delete()

    missing_response = _post_plan(client, body)
    assert missing_response.status_code == 200
    missing = missing_response.json()
    assert "data_updated_on" in missing
    assert missing.pop("data_updated_on") is None
    assert missing == present
    assert not NetworkDataVersion.objects.exists()


def test_route_save_refreshes_data_updated_on(client, net, monkeypatch):
    from datetime import datetime, timezone

    from transit.models import NetworkDataVersion
    from transit.planner import loader

    old_time = datetime(2026, 10, 1, tzinfo=timezone.utc)
    edit_time = datetime(2026, 10, 17, 17, tzinfo=timezone.utc)
    NetworkDataVersion.objects.filter(
        pk=NetworkDataVersion.SINGLETON_ID
    ).update(updated_at=old_time)
    before = NetworkDataVersion.objects.get(
        pk=NetworkDataVersion.SINGLETON_ID
    ).version

    monkeypatch.setattr(loader.timezone, "now", lambda: edit_time)
    route = net["routes"]["A"]
    route.name = "Updated test route"
    route.save()

    row = NetworkDataVersion.objects.get(
        pk=NetworkDataVersion.SINGLETON_ID
    )
    assert row.version == before + 1
    assert row.updated_at == edit_time

    response = _post_plan(client, {
        "origin": {"latitude": 10.300, "longitude": 123.900},
        "destination": {"latitude": 10.300, "longitude": 123.927},
    })
    assert response.status_code == 200
    assert response.json()["data_updated_on"] == "2026-10-18"
