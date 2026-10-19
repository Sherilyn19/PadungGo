"""Regression tests for list-endpoint query parameters (limit, area_id, cursor).

Bug fixes (API behavior changes, Oct 2026):
* `limit` outside 1–50 or non-integer -> 400 (was silently replaced).
* malformed `area_id` / `cursor` -> 400 (was a 503 or ignored).
* `area_id` on /routes now filters (was ignored).
* `cursor` now continues after the previous page (was ignored -> page 1 again).
"""
from __future__ import annotations

import pytest
from django.test import Client

from transit.models import Area, Location
from transit.tests.db_fixtures import build_verified_network

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


@pytest.mark.parametrize("bad", ["abc", "0", "-3", "51", "2.5"])
@pytest.mark.parametrize("path", ["/api/v1/locations", "/api/v1/routes"])
def test_invalid_limit_is_rejected(client, path, bad):
    resp = client.get(path, {"limit": bad})
    assert resp.status_code == 400
    error = resp.json()["error"]
    assert error["code"] == "invalid_request"
    assert "limit" in error["fields"]


@pytest.mark.parametrize("param", ["area_id", "cursor"])
@pytest.mark.parametrize("path", ["/api/v1/locations", "/api/v1/routes"])
def test_malformed_ids_are_rejected(client, path, param):
    resp = client.get(path, {param: "not-a-uuid"})
    assert resp.status_code == 400
    assert param in resp.json()["error"]["fields"]


def test_routes_area_filter(client):
    net = build_verified_network()
    area = Area.objects.create(name="Test Barangay", kind="barangay")
    # Stop Two is served only by route A1.
    stop = net["stops"]["Stop Two"]
    stop.area = area
    stop.save()

    resp = client.get("/api/v1/routes", {"area_id": str(area.id)})
    assert resp.status_code == 200
    assert [r["code"] for r in resp.json()["results"]] == ["A1"]


def test_locations_cursor_returns_next_page(client):
    for name in ["Alpha", "Bravo", "Charlie", "Delta", "Echo"]:
        Location.objects.create(name=name, kind="place", latitude=10.3, longitude=123.9)

    first = client.get("/api/v1/locations", {"limit": 2}).json()
    assert [r["name"] for r in first["results"]] == ["Alpha", "Bravo"]
    second = client.get("/api/v1/locations", {"limit": 2, "cursor": first["next_cursor"]}).json()
    assert [r["name"] for r in second["results"]] == ["Charlie", "Delta"]
    third = client.get("/api/v1/locations", {"limit": 2, "cursor": second["next_cursor"]}).json()
    assert [r["name"] for r in third["results"]] == ["Echo"]
    assert third["next_cursor"] is None


def test_routes_cursor_returns_next_page(client):
    build_verified_network()
    first = client.get("/api/v1/routes", {"limit": 1}).json()
    second = client.get("/api/v1/routes", {"limit": 1, "cursor": first["next_cursor"]}).json()
    assert [r["code"] for r in first["results"]] == ["A1"]
    assert [r["code"] for r in second["results"]] == ["B2"]
    assert second["next_cursor"] is None


def test_valid_limit_still_accepted(client):
    assert client.get("/api/v1/locations", {"q": "x", "limit": 8}).status_code == 200
