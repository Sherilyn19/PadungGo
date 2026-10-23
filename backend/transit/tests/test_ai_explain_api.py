"""POST /journeys/explain with the AI provider faked. No test reaches the network.

The synthetic database network is test-only data, never shown to commuters.
"""
from __future__ import annotations

import io
import json
import logging
import socket
import urllib.error
import uuid

import pytest
from django.core.cache import cache
from django.test import Client

from transit.models import FareRule, Location, ProviderUsage, Route, RoutePattern
from transit.planner.loader import invalidate_network_cache
from transit.tests.db_fixtures import build_verified_network

pytestmark = pytest.mark.django_db

PLAN_URL = "/api/v1/journeys/plan"
EXPLAIN_URL = "/api/v1/journeys/explain"
SECRET_KEY = "sk-test-secret-value"
PROVIDER_URL = "https://ai.example.test/v1"

# Search points. Coordinates must never reach the AI provider or the logs.
ONE = {"latitude": 10.300, "longitude": 123.900}
TWO = {"latitude": 10.300, "longitude": 123.927}        # direct trip A1
FAR = {"latitude": 10.3005, "longitude": 123.936}       # one-transfer trip A1 + B2

DIRECT_OK = ("Board A1 at Stop One and get off at Stop Four. The ride takes about 15 minutes. "
             "The fare is ₱13.00. Waiting time is unknown, so allow extra time.")
TRANSFER_OK = ("Take A1 at Stop One and get off at Stop Three. Walk to Stop Five, then take B2 and get off at "
               "Stop Seven. The fare is ₱26.00. Waiting time is unknown.")


@pytest.fixture(autouse=True)
def isolated(settings):
    cache.clear()
    settings.AI = {**settings.AI, "BASE_URL": PROVIDER_URL, "API_KEY": SECRET_KEY,
                   "MODEL": "test/open-model", "DAILY_REQUEST_LIMIT": 100}
    yield
    cache.clear()


@pytest.fixture
def net():
    return build_verified_network()


@pytest.fixture
def client():
    return Client()


class FakeProvider:
    """Stands in for urllib.request.urlopen; records what was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.sent = []

    def __call__(self, request, timeout=None):
        self.sent.append({"url": request.full_url, "headers": dict(request.header_items()),
                          "body": json.loads(request.data), "timeout": timeout})
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, BaseException):
            raise reply
        return reply

    @property
    def calls(self):
        return len(self.sent)

    @property
    def prompt(self):
        return "\n".join(m["content"] for m in self.sent[0]["body"]["messages"])


def reply(text, finish_reason="stop"):
    body = {"choices": [{"message": {"content": text}, "finish_reason": finish_reason}]}
    return _Response(json.dumps(body).encode())


class _Response:
    """Can be read again on every attempt, like a fresh HTTP response."""

    def __init__(self, data: bytes):
        self.data = data

    def read(self, size=-1):
        return self.data if size < 0 else self.data[:size]

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def http_error(code):
    return urllib.error.HTTPError(PROVIDER_URL, code, "x", {}, io.BytesIO(b'{"error":"secret detail"}'))


@pytest.fixture
def provider(monkeypatch):
    def install(*replies):
        fake = FakeProvider(*replies)
        monkeypatch.setattr("transit.ai.provider.urllib.request.urlopen", fake)
        return fake
    return install


def search(origin, destination, **extra):
    return {"origin": origin, "destination": destination, **extra}


def chosen(client, origin, destination, transfers):
    """Plan like the app does, then pick the first trip with that many transfers."""
    plan = client.post(PLAN_URL, search(origin, destination), content_type="application/json").json()
    option = next(o for o in plan["journey_options"] if o["transfers"] == transfers)
    rides = [{k: s[k] for k in ("route_pattern_id", "board_occurrence_id", "alight_occurrence_id")}
             for s in option["segments"] if s["mode"] == "ride"]
    return rides


def explain(client, origin, destination, rides, **extra):
    body = {**search(origin, destination), "rides": rides, **extra}
    return client.post(EXPLAIN_URL, json.dumps(body), content_type="application/json")


def explain_direct(client, **extra):
    return explain(client, ONE, TWO, chosen(client, ONE, TWO, 0), **extra)


def explain_transfer(client, **extra):
    return explain(client, ONE, FAR, chosen(client, ONE, FAR, 1), **extra)


# --- Successful explanations ------------------------------------------------


def test_direct_trip_is_explained_and_labelled_ai_generated(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    resp = explain_direct(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok" and body["ai_generated"] is True
    assert body["explanation"] == DIRECT_OK
    assert body["model"] == "test/open-model"
    assert fake.calls == 1


def test_transfer_trip_is_explained_with_both_routes_in_order(client, net, provider):
    provider(reply(TRANSFER_OK))
    body = explain_transfer(client).json()
    assert body["status"] == "ok"
    assert body["explanation"].index("A1") < body["explanation"].index("B2")


def test_unknown_fare_stays_unknown(client, net, provider):
    FareRule.objects.update(status="documented")
    fake = provider(reply("Take A1 from Stop One to Stop Four. The fare is unknown, so ask the driver. "
                          "Waiting time is unknown."))
    body = explain_direct(client).json()
    assert body["status"] == "ok"
    assert '"fare": {"known": false}' in fake.prompt
    assert any("Total fare unavailable" in n for n in body["notices"])
    assert "Waiting time is unknown: no verified frequency data." in body["notices"]


def test_historic_data_keeps_the_not_field_verified_warning(client, net, provider, settings):
    settings.PLANNER = {**settings.PLANNER, "ALLOW_DOCUMENTED": True}
    RoutePattern.objects.update(status="documented")
    invalidate_network_cache()
    fake = provider(reply("Take A1 from Stop One to Stop Four. This is historic data and not field-verified, so "
                          "confirm the jeepney still runs. The fare is unknown, so ask the driver. The wait is unknown."))
    body = explain_direct(client).json()
    assert body["status"] == "ok"
    assert "historic_not_field_verified" in fake.prompt
    assert any("not field-verified" in n for n in body["notices"])


def test_scarce_service_is_passed_on_and_must_be_mentioned(client, net, provider):
    Route.objects.filter(code="A1").update(service_availability="scarce")
    invalidate_network_cache()
    fake = provider(reply("Take A1 from Stop One to Stop Four. A1 is scarce, so few trips are reported. "
                          "The fare is ₱13.00. The wait is unknown."))
    body = explain_direct(client).json()
    assert body["status"] == "ok"
    assert '"scarce_service": true' in fake.prompt
    assert any("A1 is flagged scarce" in n for n in body["notices"])


def test_trip_can_be_chosen_from_saved_place_ids(client, net, provider):
    start = Location.objects.create(name="Near One", kind="place", latitude=10.300, longitude=123.900, status="verified")
    provider(reply(DIRECT_OK))
    rides = chosen(client, ONE, TWO, 0)
    resp = explain(client, {"location_id": str(start.id)}, TWO, rides)
    assert resp.json()["status"] == "ok"


def test_same_trip_is_explained_once_then_served_from_cache(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    assert explain_direct(client).json()["explanation"] == DIRECT_OK
    assert explain_direct(client).json()["explanation"] == DIRECT_OK
    assert fake.calls == 1


# --- What the provider receives ----------------------------------------------


def test_provider_gets_minimal_facts_and_the_key_only_in_a_header(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    explain_direct(client)
    sent = fake.sent[0]
    assert sent["url"] == f"{PROVIDER_URL}/chat/completions"
    assert sent["headers"]["Authorization"] == f"Bearer {SECRET_KEY}"
    assert SECRET_KEY not in json.dumps(sent["body"])
    assert sent["body"]["model"] == "test/open-model"
    assert "A1" in fake.prompt and "Stop One" in fake.prompt
    for private in ("10.30", "123.9", "latitude", "longitude"):
        assert private not in fake.prompt


def test_response_to_the_browser_never_contains_the_key(client, net, provider):
    provider(reply(DIRECT_OK))
    assert SECRET_KEY not in explain_direct(client).content.decode()


def test_nothing_sensitive_is_logged(client, net, provider, caplog):
    caplog.set_level(logging.DEBUG)
    provider(reply("Take A1 at Stop One then ₱99 and a 63C bus."), http_error(401))
    explain_direct(client)
    for private in (SECRET_KEY, "10.30", "123.9", "Stop One", "63C", "secret detail"):
        assert private not in caplog.text


# --- Malformed input and attempted fabrication -------------------------------


def valid_ride():
    return {"route_pattern_id": str(uuid.uuid4()), "board_occurrence_id": str(uuid.uuid4()),
            "alight_occurrence_id": str(uuid.uuid4())}


@pytest.mark.parametrize("rides", [
    [], "A1", None, {"route_code": "A1"},
    [valid_ride(), valid_ride(), valid_ride()],
    [{"route_pattern_id": "not-a-uuid", "board_occurrence_id": "x", "alight_occurrence_id": "y"}],
    [{"route_pattern_id": str(uuid.uuid4())}],
])
def test_malformed_rides_are_rejected_without_calling_the_provider(client, net, provider, rides):
    fake = provider(reply(DIRECT_OK))
    resp = explain(client, ONE, TWO, rides)
    assert resp.status_code == 400 and resp.json()["error"]["code"] == "invalid_request"
    assert fake.calls == 0


@pytest.mark.parametrize("body", [
    "not json", "[]", "null", "{}",
    json.dumps({"origin": ONE}),
    json.dumps({"origin": {"latitude": 999, "longitude": 1}, "destination": TWO, "rides": [{}]}),
])
def test_malformed_bodies_are_rejected(client, net, provider, body):
    fake = provider(reply(DIRECT_OK))
    resp = client.post(EXPLAIN_URL, body, content_type="application/json")
    assert resp.status_code == 400
    assert fake.calls == 0


@pytest.mark.parametrize("extra", [
    {"fare": "₱1.00"}, {"explanation": "Take 99Z"}, {"facts": {"route_code": "99Z"}},
    {"stops": ["Fake Stop"]}, {"notices": []},
])
def test_client_cannot_supply_trip_facts(client, net, provider, extra):
    fake = provider(reply(DIRECT_OK))
    resp = explain_direct(client, **extra)
    assert resp.status_code == 400
    assert list(extra)[0] in resp.json()["error"]["fields"]
    assert fake.calls == 0


def test_client_cannot_smuggle_facts_inside_a_ride(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    rides = chosen(client, ONE, TWO, 0)
    rides[0]["route_code"] = "99Z"
    rides[0]["board_stop_name"] = "Made-up Stop"
    resp = explain(client, ONE, TWO, rides)
    assert resp.status_code == 400
    assert fake.calls == 0


def test_invented_ride_ids_do_not_match_any_planned_trip(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    resp = explain(client, ONE, TWO, [valid_ride()])
    assert resp.status_code == 404 and resp.json()["error"]["code"] == "not_found"
    assert fake.calls == 0


def test_real_ids_from_a_different_search_are_not_accepted(client, net, provider):
    fake = provider(reply(DIRECT_OK))
    rides = chosen(client, ONE, TWO, 0)
    # The same rides do not belong to a search that never plans them.
    resp = explain(client, ONE, {"latitude": 10.3005, "longitude": 123.936}, rides)
    assert resp.status_code == 404
    assert fake.calls == 0


def test_a_partial_trip_is_not_accepted(client, net, provider):
    fake = provider(reply(TRANSFER_OK))
    rides = chosen(client, ONE, FAR, 1)
    resp = explain(client, ONE, FAR, rides[:1])
    assert resp.status_code == 404
    assert fake.calls == 0


def test_unknown_saved_place_is_a_400(client, net, provider):
    rides = chosen(client, ONE, TWO, 0)
    resp = explain(client, {"location_id": str(uuid.uuid4())}, TWO, rides)
    assert resp.status_code == 400


@pytest.mark.parametrize("fabricated,reason_hint", [
    ("Take A1 from Stop One to Stop Four, then ride 63C. The fare is ₱13.00. The wait is unknown.", "route"),
    ("Take A1 from Stop One to Stop Four. The fare is ₱20.00. The wait is unknown.", "price"),
    ("Take A1 from Stop One to Stop Four. It takes 5 minutes. The fare is ₱13.00. The wait is unknown.", "time"),
    ("Take A1 from Stop One to Stop Four. Jeepneys run every 5 minutes. The fare is ₱13.00. The wait is unknown.", "frequency"),
    ("Take A1 from Stop One to Stop Four, near the Colon church. The fare is ₱13.00. The wait is unknown.", "landmark"),
    ("Take A1 from Stop One to Stop Four. The fare is ₱13.00.", "dropped warning"),
])
def test_model_that_invents_facts_is_never_shown(client, net, provider, fabricated, reason_hint):
    fake = provider(reply(fabricated))
    body = explain_direct(client).json()
    assert body["status"] == "unavailable" and body["reason"] == "invalid_output" and body["retryable"] is True
    assert "explanation" not in body
    assert fake.calls == 2   # one retry, then give up


def test_invalid_first_answer_is_retried_once_with_the_failed_check(client, net, provider):
    fake = provider(reply("Take A1 from Stop One to Stop Four. The fare is ₱99.00. The wait is unknown."),
                    reply(DIRECT_OK))
    body = explain_direct(client).json()
    assert body["status"] == "ok" and body["explanation"] == DIRECT_OK
    assert fake.calls == 2
    assert "wrong_fare" in fake.sent[1]["body"]["messages"][-1]["content"]


def test_invalid_answers_are_not_cached(client, net, provider):
    fake = provider(reply("Take A1 from Stop One to Stop Four. The fare is ₱20.00. The wait is unknown."))
    explain_direct(client)
    explain_direct(client)
    assert fake.calls == 4


# --- Provider failures ------------------------------------------------------


@pytest.mark.parametrize("failure,reason,retryable", [
    (TimeoutError(), "timeout", True),
    (socket.timeout(), "timeout", True),
    (urllib.error.URLError(socket.timeout()), "timeout", True),
    (urllib.error.URLError("refused"), "error", True),
    (http_error(500), "error", True),
    (http_error(401), "error", True),
    (http_error(429), "rate_limited", True),
    (OSError("connection reset"), "error", True),
])
def test_provider_failure_is_reported_safely(client, net, provider, failure, reason, retryable):
    provider(failure)
    resp = explain_direct(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unavailable" and body["reason"] == reason and body["retryable"] is retryable
    assert body["message"]
    for leaked in (SECRET_KEY, "secret detail", "refused", "connection reset"):
        assert leaked not in resp.content.decode()


def test_provider_timeout_does_not_break_the_planner(client, net, provider):
    provider(TimeoutError())
    assert explain_direct(client).json()["reason"] == "timeout"
    plan = client.post(PLAN_URL, search(ONE, TWO), content_type="application/json")
    assert plan.status_code == 200 and plan.json()["journey_options"]


def test_request_to_the_provider_has_a_timeout(client, net, provider, settings):
    settings.AI = {**settings.AI, "TIMEOUT_SECONDS": 7.0}
    fake = provider(reply(DIRECT_OK))
    explain_direct(client)
    assert fake.sent[0]["timeout"] == 7.0


@pytest.mark.parametrize("bad", [
    _Response(b"<html>gateway</html>"), _Response(b"{}"), _Response(b'{"choices": []}'),
    _Response(b'{"choices": [{"message": {"content": null}}]}'),
    _Response(b"x" * (64 * 1024 + 10)),
])
def test_malformed_provider_reply_is_an_error_not_a_crash(client, net, provider, bad):
    provider(bad)
    body = explain_direct(client).json()
    assert body["status"] == "unavailable" and body["reason"] in ("error", "invalid_output")


def test_reply_cut_off_by_the_token_limit_is_not_used(client, net, provider):
    fake = provider(reply(DIRECT_OK, finish_reason="length"))
    body = explain_direct(client).json()
    assert body["status"] == "unavailable" and body["reason"] == "invalid_output"
    assert fake.calls == 2


def test_rate_limited_provider_is_paused_briefly(client, net, provider):
    fake = provider(http_error(429))
    assert explain_direct(client).json()["reason"] == "rate_limited"
    assert explain_direct(client).json()["reason"] == "rate_limited"
    assert fake.calls == 1   # second request did not hit the provider again


def test_rejected_key_pauses_calls(client, net, provider):
    fake = provider(http_error(401))
    explain_direct(client)
    explain_direct(client)
    assert fake.calls == 1


@pytest.mark.parametrize("override", [
    {"API_KEY": ""}, {"MODEL": ""}, {"BASE_URL": ""},
    {"BASE_URL": "http://ai.example.test/v1"},   # plain HTTP to a remote host is refused
    {"BASE_URL": "ftp://ai.example.test"},
])
def test_unconfigured_feature_is_unavailable_without_a_call(client, net, provider, settings, override):
    settings.AI = {**settings.AI, **override}
    fake = provider(reply(DIRECT_OK))
    resp = explain_direct(client)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "unavailable" and body["reason"] == "not_configured" and body["retryable"] is False
    assert fake.calls == 0


def test_daily_quota_stops_calls(client, net, provider, settings):
    settings.AI = {**settings.AI, "DAILY_REQUEST_LIMIT": 1}
    fake = provider(reply("Take A1 from Stop One to Stop Four. The fare is ₱99.00. The wait is unknown."))
    body = explain_direct(client).json()   # attempt 1 is rejected, attempt 2 finds the quota used
    assert body["reason"] == "quota" and body["retryable"] is False
    assert fake.calls == 1
    assert ProviderUsage.objects.get(provider="ai").requests == 1


def test_zero_daily_limit_turns_the_feature_off(client, net, provider, settings):
    settings.AI = {**settings.AI, "DAILY_REQUEST_LIMIT": 0}
    fake = provider(reply(DIRECT_OK))
    assert explain_direct(client).json()["reason"] == "quota"
    assert fake.calls == 0


# --- Throttling ---------------------------------------------------------------


def test_explanations_are_limited_per_visitor(client, net, provider, settings):
    provider(reply(DIRECT_OK))
    rides = chosen(client, ONE, TWO, 0)
    results = [explain(client, ONE, TWO, rides).status_code for _ in range(8)]
    assert results[:6] == [200] * 6
    assert results[6] == 429
    blocked = explain(client, ONE, TWO, rides)
    assert blocked.json()["error"]["code"] == "rate_limited" and blocked["Retry-After"]


def test_other_visitors_are_not_blocked_by_a_heavy_one(client, net, provider):
    provider(reply(DIRECT_OK))
    rides = chosen(client, ONE, TWO, 0)
    for _ in range(8):
        explain(client, ONE, TWO, rides)
    other = client.post(EXPLAIN_URL, json.dumps({**search(ONE, TWO), "rides": rides}),
                        content_type="application/json", REMOTE_ADDR="203.0.113.9")
    assert other.status_code == 200


def test_only_post_is_allowed(client, net):
    assert client.get(EXPLAIN_URL).status_code == 405
