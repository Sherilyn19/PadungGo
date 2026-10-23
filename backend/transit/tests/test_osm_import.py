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


# --- Reliability: retries, exact error messages, file fallback, Admin page ---

import io  # noqa: E402
import json  # noqa: E402
import urllib.error  # noqa: E402

from django.contrib.auth.models import User  # noqa: E402
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402


@pytest.fixture
def network(monkeypatch):
    """Fake the Overpass server: queue replies (bytes or exceptions); no real waiting."""
    replies, calls = [], []
    monkeypatch.setattr(osm_import.time, "sleep", lambda seconds: None)

    def fake_urlopen(request, timeout):
        calls.append(timeout)
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(reply)

    monkeypatch.setattr(osm_import.urllib.request, "urlopen", fake_urlopen)
    return replies, calls


def _http(code):
    return urllib.error.HTTPError("x", code, "msg", {}, None)


def test_busy_server_is_retried_then_succeeds(network):
    replies, calls = network
    replies += [_http(502), b"<html>busy</html>", json.dumps(_reply()).encode()]
    report = osm_import.import_osm_places("Cebu City")
    assert len(calls) == 3 and report.created == 2
    assert report.download_seconds is not None and report.save_seconds >= 0


@pytest.mark.parametrize("failure,expected", [
    (_http(406), "refused this app's request (HTTP 406)"),
    (_http(429), "limiting how often it can be asked (HTTP 429)"),
    (TimeoutError(), "no answer within"),
    (urllib.error.URLError("Name or service not known"), "could not connect (Name or service"),
])
def test_final_message_names_the_real_cause(network, failure, expected):
    replies, calls = network
    replies += [failure] * osm_import.MAX_ATTEMPTS
    with pytest.raises(osm_import.OSMImportError) as caught:
        osm_import.import_osm_places("Mandaue")
    assert expected in str(caught.value)
    assert "Nothing was changed" in str(caught.value)
    assert Location.objects.count() == 0


def test_refusal_is_not_retried(network):
    replies, calls = network
    replies.append(_http(406))
    with pytest.raises(osm_import.OSMImportError):
        osm_import.import_osm_places("Mandaue")
    assert len(calls) == 1


def test_query_cut_short_by_the_server_is_rejected(network):
    replies, _ = network
    partial = {**_reply(), "remark": "runtime error: Query timed out in \"query\" at line 3"}
    replies += [json.dumps(partial).encode()] * osm_import.MAX_ATTEMPTS
    with pytest.raises(osm_import.OSMImportError, match="stopped the query early"):
        osm_import.import_osm_places("Cebu City")
    assert Location.objects.count() == 0  # a partial list must not be saved


def test_each_city_has_its_own_query():
    assert '"^(Lapu-Lapu)$"' in osm_import.overpass_query("Lapu-Lapu")
    with pytest.raises(ValueError):
        osm_import.overpass_query("Talisay")


@pytest.fixture
def staff(client):
    User.objects.create_superuser("owner-test", "o@example.com", "test-only-password")
    client.login(username="owner-test", password="test-only-password")
    return client


def test_powershell_commands_are_safe_and_identify_the_app():
    for city in osm_import.CITY_NAMES:
        command = osm_import.powershell_download_command(city)
        assert "'" not in osm_import.overpass_query(city)  # cannot break out of the quoted string
        assert osm_import.USER_AGENT in command
        assert f"^({city})$" in command
        assert command.rstrip().endswith(f"-OutFile '{city.lower().replace(' ', '-')}.json'")


def test_admin_page_offers_city_choice_and_powershell_commands(staff):
    page = staff.get("/admin/transit/location/import-osm/").content.decode()
    assert "Invoke-WebRequest" in page
    assert "-OutFile &#x27;lapu-lapu.json&#x27;" in page or "-OutFile 'lapu-lapu.json'" in page
    assert "<a href=\"https://overpass" not in page  # no dead browser links


def test_admin_file_upload_imports_places(staff):
    upload = SimpleUploadedFile("cebu.json", json.dumps(_reply()).encode(), content_type="application/json")
    page = staff.post("/admin/transit/location/import-osm/", {"file": upload}).content.decode()
    assert "Done. 2 added" in page
    assert Location.objects.filter(external_ref__startswith="osm:").count() == 2


def test_admin_shows_exact_error_with_readable_colours(staff, network):
    replies, _ = network
    replies += [_http(502)] * osm_import.MAX_ATTEMPTS
    page = staff.post("/admin/transit/location/import-osm/", {"city": "Lapu-Lapu"}).content.decode()
    assert "overloaded or restarting (HTTP 502)" in page
    # Dark text on the pale banner, so it reads in Admin's dark theme too.
    assert "background:#fdecea;color:#5c1410" in page


def test_admin_rejects_a_file_that_is_not_overpass_data(staff):
    upload = SimpleUploadedFile("bad.json", b"<html>not data</html>")
    page = staff.post("/admin/transit/location/import-osm/", {"file": upload}).content.decode()
    assert "This file cannot be used" in page
