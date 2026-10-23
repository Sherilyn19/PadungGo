"""Address labels and place suggestions, with the Geoapify service faked.

Synthetic test-only places; tests never contact the real provider.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.parse

import pytest
from django.core.cache import cache

from transit.models import Location, ProviderUsage
from transit.places import geoapify

pytestmark = pytest.mark.django_db

ADDRESS_URL = "/api/v1/places/address"
SUGGEST_URL = "/api/v1/places/suggestions"
PIN = {"latitude": 10.300123, "longitude": 123.901234}


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def provider(settings, monkeypatch):
    """Enable the provider with a fake key and record each request it would send."""
    settings.GEOAPIFY = {**settings.GEOAPIFY, "API_KEY": "test-only-key", "DAILY_REQUEST_LIMIT": 10}
    calls = []
    replies = []

    def fake_urlopen(request, timeout):
        calls.append(urllib.parse.urlparse(request.full_url))
        reply = replies.pop(0) if replies else {"results": []}
        if isinstance(reply, Exception):
            raise reply
        return io.BytesIO(json.dumps(reply).encode())

    monkeypatch.setattr(geoapify.urllib.request, "urlopen", fake_urlopen)
    return calls, replies


def _reverse_result(distance=12.0):
    return {"results": [{
        "formatted": "Osmeña Boulevard, Cebu City, Philippines",
        "lat": 10.3002, "lon": 123.9013, "distance": distance,
        "datasource": {"attribution": "© OpenStreetMap contributors",
                       "url": "https://www.openstreetmap.org/copyright"},
    }]}


def test_address_without_key_is_unavailable_and_keeps_coordinates(client):
    body = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    assert body["status"] == "unavailable"
    assert body["reason"] == "disabled"
    assert (body["latitude"], body["longitude"]) == (PIN["latitude"], PIN["longitude"])


def test_resolved_address_never_moves_the_point(client, provider):
    calls, replies = provider
    replies.append(_reverse_result())
    response = client.post(ADDRESS_URL, PIN, content_type="application/json")
    body = response.json()

    assert body["status"] == "resolved"
    assert body["label"] == "Osmeña Boulevard, Cebu City, Philippines"
    assert (body["latitude"], body["longitude"]) == (PIN["latitude"], PIN["longitude"])
    assert {a["text"] for a in body["attribution"]} == {
        "Powered by Geoapify", "© OpenStreetMap contributors"}
    assert calls[0].path.endswith("/reverse")
    assert b"test-only-key" not in response.content


def test_far_match_is_not_shown_as_the_address(client, provider):
    _, replies = provider
    replies.append(_reverse_result(distance=400))
    body = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    assert body["status"] == "no_result"
    assert body["label"] is None


def test_repeat_lookup_uses_cache(client, provider):
    calls, replies = provider
    replies.append(_reverse_result())
    client.post(ADDRESS_URL, PIN, content_type="application/json")
    second = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    assert second["status"] == "resolved"
    assert len(calls) == 1


def test_rate_limit_pauses_further_requests(client, provider):
    calls, replies = provider
    replies.append(urllib.error.HTTPError("x", 429, "Too Many Requests", {}, None))
    first = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    other = {"latitude": 10.31, "longitude": 123.91}
    second = client.post(ADDRESS_URL, other, content_type="application/json").json()
    assert first["reason"] == second["reason"] == "rate_limited"
    assert len(calls) == 1


def test_timeout_is_reported(client, provider):
    _, replies = provider
    replies.append(TimeoutError())
    body = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    assert (body["status"], body["reason"]) == ("unavailable", "timeout")


def test_daily_limit_stops_requests(client, provider, settings):
    calls, _ = provider
    settings.GEOAPIFY = {**settings.GEOAPIFY, "DAILY_REQUEST_LIMIT": 1}
    client.post(ADDRESS_URL, PIN, content_type="application/json")
    other = {"latitude": 10.31, "longitude": 123.91}
    body = client.post(ADDRESS_URL, other, content_type="application/json").json()
    assert body["reason"] == "quota"
    assert len(calls) == 1
    assert ProviderUsage.objects.get().requests == 1


@pytest.mark.parametrize("payload", [{}, {"latitude": 91, "longitude": 0}, {"latitude": "x"}])
def test_invalid_point_is_rejected(client, payload):
    response = client.post(ADDRESS_URL, payload, content_type="application/json")
    assert response.status_code == 400


def test_address_rejects_get(client):
    assert client.get(ADDRESS_URL).status_code == 405


@pytest.fixture
def campuses():
    # Two separately named campuses sharing one alias, plus an accented name.
    for name in ("Example Tech University - North Campus", "Example Tech University - South Campus"):
        Location.objects.create(name=name, aliases="ETU", kind="school",
                                latitude=10.30, longitude=123.90)
    Location.objects.create(name="Fuente Osmeña Circle", kind="landmark",
                            latitude=10.31, longitude=123.89)
    Location.objects.create(name="Etuy Street", kind="place", latitude=10.32, longitude=123.88)


def test_alias_lists_every_campus_first(client, campuses):
    results = client.get(SUGGEST_URL, {"q": "etu"}).json()["results"]
    names = [r["name"] for r in results]
    assert names[:2] == ["Example Tech University - North Campus",
                         "Example Tech University - South Campus"]
    assert "Etuy Street" in names
    # The acronym is also worked out from the name, with no alias typed.
    by_acronym = [r["name"] for r in client.get(SUGGEST_URL, {"q": "ETU"}).json()["results"]]
    assert by_acronym[:2] == names[:2]
    assert all(r["source"] == "padunggo" and r["location_id"] for r in results)


@pytest.mark.parametrize("query", ["osmena", "OSMEÑA", "Osmeña circle"])
def test_case_and_accent_insensitive(client, campuses, query):
    names = [r["name"] for r in client.get(SUGGEST_URL, {"q": query}).json()["results"]]
    assert names == ["Fuente Osmeña Circle"]


def test_locations_endpoint_matches_accents_and_aliases(client, campuses):
    names = [r["name"] for r in client.get("/api/v1/locations", {"q": "osmena"}).json()["results"]]
    assert names == ["Fuente Osmeña Circle"]
    # Word beginnings only: "etu" matches "ETU" and "Etuy", not words containing it.
    assert len(client.get("/api/v1/locations", {"q": "ETU"}).json()["results"]) == 3


def test_provider_results_are_labelled_and_deduplicated(client, campuses, provider):
    calls, replies = provider
    replies.append({"results": [
        # Same place as a curated record: dropped.
        {"name": "Fuente Osmeña Circle", "lat": 10.3101, "lon": 123.8901, "city": "Cebu City",
         "address_line2": "Cebu City", "category": "tourism.attraction"},
        {"name": "Osmeña Bakery", "lat": 10.29, "lon": 123.90, "city": "Cebu City",
         "address_line2": "Colon Street, Cebu City", "category": "commercial.food_and_drink"},
        # Outside Cebu City, Mandaue and Lapu-Lapu: dropped.
        {"name": "Osmeña Store", "lat": 10.25, "lon": 123.84, "city": "Talisay"},
    ]})
    body = client.get(SUGGEST_URL, {"q": "osmena"}).json()

    assert [r["source"] for r in body["results"]] == ["padunggo", "geoapify"]
    added = body["results"][1]
    assert added["location_id"] is None
    assert added["kind"] == "business"
    assert body["provider"]["status"] == "ok"
    assert body["provider"]["attribution"]
    params = urllib.parse.parse_qs(calls[0].query)
    assert params["filter"][0].startswith("rect:")


def test_suggestion_cache_ignores_case(client, provider):
    calls, _ = provider
    client.get(SUGGEST_URL, {"q": "Ayala"})
    client.get(SUGGEST_URL, {"q": "ayala"})
    assert len(calls) == 1


def test_short_query_does_not_use_provider(client, provider):
    calls, _ = provider
    body = client.get(SUGGEST_URL, {"q": "sm"}).json()
    assert body["provider"]["status"] == "skipped"
    assert calls == []


def test_suggestions_keep_daily_reserve_for_addresses(client, provider, settings):
    calls, _ = provider
    settings.GEOAPIFY = {**settings.GEOAPIFY, "DAILY_REQUEST_LIMIT": 2, "SUGGEST_SHARE": 0.5}
    client.get(SUGGEST_URL, {"q": "ayala"})
    body = client.get(SUGGEST_URL, {"q": "colon"}).json()
    assert body["provider"]["status"] == "quota"
    address = client.post(ADDRESS_URL, PIN, content_type="application/json").json()
    # The reserved share still lets the address lookup reach the provider.
    assert address["status"] == "no_result"
    assert len(calls) == 2


@pytest.fixture
def universities():
    for name, kind in (("University of San Jose-Recoletos", "school"),
                       ("Cebu Normal University", "school"),
                       ("Normal Street", "place"),
                       ("Mactan-Cebu International Airport", "transport_hub")):
        Location.objects.create(name=name, kind=kind, latitude=10.3, longitude=123.9)


@pytest.mark.parametrize("query,first", [
    ("usjr", "University of San Jose-Recoletos"),
    ("USJ", "University of San Jose-Recoletos"),
    ("cnu", "Cebu Normal University"),
    ("mcia", "Mactan-Cebu International Airport"),
    ("san jose", "University of San Jose-Recoletos"),
])
def test_acronyms_and_word_beginnings(client, universities, query, first):
    assert client.get(SUGGEST_URL, {"q": query}).json()["results"][0]["name"] == first


def test_word_inside_name_is_found(client, universities):
    names = [r["name"] for r in client.get(SUGGEST_URL, {"q": "normal"}).json()["results"]]
    assert set(names) == {"Normal Street", "Cebu Normal University"}


def test_one_letter_suggests_without_provider(client, universities, provider):
    calls, _ = provider
    body = client.get(SUGGEST_URL, {"q": "u"}).json()
    assert body["results"][0]["name"] == "University of San Jose-Recoletos"
    assert body["provider"]["status"] == "skipped"
    assert calls == []


def test_middle_of_word_does_not_match(client, universities):
    assert client.get(SUGGEST_URL, {"q": "ormal"}).json()["results"] == []
