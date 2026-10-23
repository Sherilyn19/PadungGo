"""OpenStreetMap place import, with a recorded-style synthetic Overpass reply."""
from __future__ import annotations

import pytest

from transit.models import Location
from transit.places import osm_import

pytestmark = pytest.mark.django_db


def _reply(name="University of San Jose-Recoletos", lat=10.2946):
    return {"elements": [
        {"type": "area", "id": 1, "tags": {"boundary": "administrative", "name": "Cebu City"}},
        {"type": "way", "id": 11, "center": {"lat": lat, "lon": 123.8978},
         "tags": {"name": name, "amenity": "university", "short_name": "USJ-R"}},
        # Same place mapped twice nearby: kept once.
        {"type": "node", "id": 12, "lat": lat + 0.0001, "lon": 123.8978,
         "tags": {"name": name, "amenity": "university"}},
        {"type": "node", "id": 13, "lat": 10.3, "lon": 123.9, "tags": {"amenity": "bank"}},  # unnamed
        {"type": "node", "id": 14, "lat": 10.3, "lon": 123.9,
         "tags": {"name": "Some Shop", "shop": "clothes"}},  # not a wanted kind
        {"type": "area", "id": 2, "tags": {"boundary": "administrative", "name": "Mandaue"}},
        {"type": "node", "id": 21, "lat": 10.33, "lon": 123.94,
         "tags": {"name": "Mandaue City Hall", "amenity": "townhall"}},
    ]}


def test_parse_keeps_named_wanted_places_with_city():
    rows = osm_import.parse_places(_reply())
    assert [(r.name, r.city, r.kind) for r in rows] == [
        ("University of San Jose-Recoletos", "Cebu City", "school"),
        ("Mandaue City Hall", "Mandaue", "landmark"),
    ]
    assert rows[0].aliases == "USJ-R"


def test_import_is_searchable_and_rerun_updates_in_place(client, monkeypatch):
    hand_made = Location.objects.create(name="My Own Place", latitude=10.3, longitude=123.9)
    monkeypatch.setattr(osm_import, "fetch_overpass", lambda q: _reply())
    first = osm_import.import_osm_places()
    assert (first.created, first.by_city) == (2, {"Cebu City": 1, "Mandaue": 1})

    results = client.get("/api/v1/places/suggestions", {"q": "usjr"}).json()["results"]
    assert results[0]["name"] == "University of San Jose-Recoletos"
    assert results[0]["detail"] == "Cebu City"

    monkeypatch.setattr(osm_import, "fetch_overpass", lambda q: _reply(lat=10.2950))
    second = osm_import.import_osm_places()
    assert (second.created, second.updated, second.unchanged) == (0, 1, 1)
    assert Location.objects.count() == 3
    hand_made.refresh_from_db()
    assert hand_made.external_ref == ""


def test_empty_reply_changes_nothing(monkeypatch):
    monkeypatch.setattr(osm_import, "fetch_overpass", lambda q: {"elements": []})
    with pytest.raises(osm_import.OSMImportError):
        osm_import.import_osm_places()
    assert Location.objects.count() == 0


def test_query_covers_only_the_three_cities():
    query = osm_import.overpass_query()
    assert '"^(Cebu City|Mandaue|Lapu-Lapu)$"' in query


def test_admin_import_page_needs_superuser(client):
    response = client.post("/admin/transit/location/import-osm/")
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
