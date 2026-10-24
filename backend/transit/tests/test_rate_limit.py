"""Trip planning is limited per visitor so a few users cannot overload the free server."""
from __future__ import annotations

import pytest
from django.core.cache import cache

PLAN_URL = "/api/v1/journeys/plan"
LIMIT = 30  # DRF_PLAN_THROTTLE default "30/min"


@pytest.fixture(autouse=True)
def fresh_counters():
    cache.clear()
    yield
    cache.clear()


def _plan(client):
    # An empty body is refused with 400, which still counts toward the limit.
    return client.post(PLAN_URL, {}, content_type="application/json")


def test_planning_is_limited_after_the_allowed_number_of_searches(client):
    assert all(_plan(client).status_code == 400 for _ in range(LIMIT))
    blocked = _plan(client)
    assert blocked.status_code == 429
    body = blocked.json()["error"]
    assert body["code"] == "rate_limited" and body["retryable"] is True
    assert "wait" in body["message"].lower() and "throttled" not in body["message"].lower()
    assert int(blocked["Retry-After"]) > 0


def test_health_check_is_never_limited(client):
    assert all(client.get("/health").status_code == 200 for _ in range(LIMIT + 5))


def test_other_visitors_are_not_blocked_by_one_heavy_visitor(client):
    for _ in range(LIMIT + 1):
        _plan(client)
    other = client.post(PLAN_URL, {}, content_type="application/json", REMOTE_ADDR="203.0.113.7")
    assert other.status_code == 400  # allowed through, then refused only for the empty body


# --- Who is the visitor? (proxy-aware identity) --------------------------------

import json  # noqa: E402

from rest_framework.throttling import SimpleRateThrottle  # noqa: E402

from transit.api.throttles import client_identity  # noqa: E402
from transit.models import ProviderUsage  # noqa: E402

PROXY = "10.0.0.1"   # Render's own proxy: the connecting address behind Cloudflare


def meta(forwarded=None, remote=PROXY):
    data = {"REMOTE_ADDR": remote}
    if forwarded is not None:
        data["HTTP_X_FORWARDED_FOR"] = forwarded
    return data


@pytest.mark.parametrize("forwarded,hops,expected", [
    (None, 0, PROXY),                                 # no proxy trusted: connecting address
    ("1.2.3.4, 9.9.9.9", 0, PROXY),                   # header ignored when no proxy is trusted
    ("1.2.3.4, 172.70.1.1", 2, "1.2.3.4"),            # Cloudflare edge is the last entry
    ("1.2.3.4, 172.70.9.9", 2, "1.2.3.4"),            # the edge changes, the visitor does not
    ("6.6.6.6, 1.2.3.4, 172.70.1.1", 2, "1.2.3.4"),   # junk the visitor adds on the left is ignored
    ("6.6.6.6, 7.7.7.7, 1.2.3.4, 172.70.1.1", 2, "1.2.3.4"),
    ("1.2.3.4", 2, PROXY),                            # chain too short: do not trust it
    ("", 2, PROXY),
    (None, 2, PROXY),
    ("not-an-ip, 172.70.1.1", 2, PROXY),              # garbage in the visitor slot
    ("2001:db8:1:2:aaaa::1, 172.70.1.1", 2, "2001:db8:1:2::/64"),   # IPv6 grouped by /64
    ("2001:db8:1:2:bbbb::9, 172.70.1.1", 2, "2001:db8:1:2::/64"),
])
def test_visitor_is_found_without_trusting_what_the_client_wrote(forwarded, hops, expected):
    assert client_identity(meta(forwarded), hops) == expected


def test_missing_connecting_address_is_one_shared_bucket_not_an_error():
    assert client_identity({}, 2) == "unknown"


@pytest.fixture
def behind_render(settings):
    settings.TRUSTED_PROXY_HOPS = 3


def plan_as(client, forwarded):
    return client.post(PLAN_URL, {}, content_type="application/json",
                       HTTP_X_FORWARDED_FOR=forwarded, REMOTE_ADDR=PROXY).status_code


def test_one_visitor_is_limited_even_when_the_proxy_address_changes(client, behind_render):
    # What production does: same visitor, a different Cloudflare edge address each time.
    codes = [plan_as(client, f"1.2.3.4, 172.70.{i // 250}.{i % 250 + 1}, 10.20.0.9") for i in range(LIMIT + 5)]
    assert codes[:LIMIT] == [400] * LIMIT and codes[LIMIT:] == [429] * 5


def test_adding_fake_addresses_does_not_escape_the_limit(client, behind_render):
    codes = [plan_as(client, f"9.9.{i // 250}.{i % 250 + 1}, 1.2.3.4, 172.70.1.1, 10.20.0.9") for i in range(LIMIT + 5)]
    assert codes.count(429) == 5


def test_different_visitors_behind_the_same_proxy_have_separate_limits(client, behind_render):
    for _ in range(LIMIT + 1):
        plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9")
    assert plan_as(client, "5.6.7.8, 172.70.1.1, 10.20.0.9") == 400   # a different visitor is still allowed
    assert plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9") == 429


def test_without_trusted_proxies_the_header_is_ignored(client, settings):
    settings.TRUSTED_PROXY_HOPS = 0
    codes = [plan_as(client, f"9.9.{i // 250}.{i % 250 + 1}") for i in range(LIMIT + 3)]
    assert codes.count(429) == 3          # all one visitor (the connecting address)


def test_limit_resets_after_the_window(client, behind_render, monkeypatch):
    now = [1_000_000.0]
    monkeypatch.setattr(SimpleRateThrottle, "timer", lambda self: now[0])
    assert [plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9") for _ in range(LIMIT)] == [400] * LIMIT
    assert plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9") == 429
    now[0] += 59
    assert plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9") == 429     # window not over yet
    now[0] += 2
    assert plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9") == 400     # a minute later it is allowed again


def test_blocked_response_names_the_wait_and_how_long(client, behind_render):
    for _ in range(LIMIT):
        plan_as(client, "1.2.3.4, 172.70.1.1, 10.20.0.9")
    blocked = client.post(PLAN_URL, {}, content_type="application/json",
                          HTTP_X_FORWARDED_FOR="1.2.3.4, 172.70.1.1, 10.20.0.9", REMOTE_ADDR=PROXY)
    assert blocked.status_code == 429 and blocked.json()["error"]["retryable"] is True
    assert 0 < int(blocked["Retry-After"]) <= 60


# --- Blocked requests never reach a paid provider --------------------------------

PLACES_LIMIT = 40
EXPLAIN_LIMIT = 6


@pytest.mark.django_db
def test_blocked_address_lookups_do_not_call_geoapify_or_use_its_quota(client, behind_render, monkeypatch):
    calls = []
    monkeypatch.setattr("transit.api.place_views.reverse_address",
                        lambda lat, lon: calls.append(1) or {"status": "unavailable"})
    body = json.dumps({"latitude": 10.3, "longitude": 123.9})
    codes = [client.post("/api/v1/places/address", body, content_type="application/json",
                         HTTP_X_FORWARDED_FOR=f"1.2.3.4, 172.70.0.{i % 200 + 1}, 10.20.0.9", REMOTE_ADDR=PROXY).status_code
             for i in range(PLACES_LIMIT + 10)]
    assert codes.count(200) == PLACES_LIMIT and codes.count(429) == 10
    assert len(calls) == PLACES_LIMIT
    assert not ProviderUsage.objects.exists()


def test_blocked_suggestion_lookups_do_not_call_geoapify(client, behind_render, monkeypatch):
    calls = []
    monkeypatch.setattr("transit.api.place_views.place_suggestions",
                        lambda q: calls.append(q) or {"results": [], "provider": {"status": "skipped"}})
    codes = [client.get("/api/v1/places/suggestions", {"q": "cebu"},
                        HTTP_X_FORWARDED_FOR="1.2.3.4, 172.70.0.1, 10.20.0.9", REMOTE_ADDR=PROXY).status_code
             for _ in range(PLACES_LIMIT + 5)]
    assert codes.count(429) == 5 and len(calls) == PLACES_LIMIT


@pytest.mark.django_db
def test_blocked_explanations_do_not_reach_the_ai_provider(client, behind_render, monkeypatch, settings):
    calls = []
    monkeypatch.setattr("transit.api.explain_views.explain_trip",
                        lambda option: calls.append(1) or pytest.fail("planner never matched, so not reached"))
    # Valid-shaped body that matches no trip: 404 each time, still counted by the limit.
    body = json.dumps({"origin": {"latitude": 10.3, "longitude": 123.9},
                       "destination": {"latitude": 10.31, "longitude": 123.91},
                       "rides": [{"route_pattern_id": "00000000-0000-4000-8000-000000000001",
                                  "board_occurrence_id": "00000000-0000-4000-8000-000000000002",
                                  "alight_occurrence_id": "00000000-0000-4000-8000-000000000003"}]})
    codes = [client.post("/api/v1/journeys/explain", body, content_type="application/json",
                         HTTP_X_FORWARDED_FOR="1.2.3.4, 172.70.0.%d, 10.20.0.9" % (i % 200 + 1), REMOTE_ADDR=PROXY).status_code
             for i in range(EXPLAIN_LIMIT + 4)]
    assert codes[:EXPLAIN_LIMIT] == [404] * EXPLAIN_LIMIT and codes[EXPLAIN_LIMIT:] == [429] * 4
    assert calls == []


def test_every_provider_endpoint_is_limited_by_visitor_not_open():
    """Guards against adding a paid-provider endpoint without a throttle."""
    from transit.api import explain_views, place_views, views
    from transit.api.throttles import ClientRateThrottle

    for view in (views.plan_journey, place_views.suggestions, place_views.address, explain_views.explain_journey):
        classes = view.cls.throttle_classes
        assert classes and all(issubclass(c, ClientRateThrottle) for c in classes), view.__name__
