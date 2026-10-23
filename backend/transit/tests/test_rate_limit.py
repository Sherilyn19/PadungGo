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
