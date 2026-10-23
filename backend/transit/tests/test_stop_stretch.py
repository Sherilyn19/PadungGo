"""Admin action that switches boarding/getting-off off or on along a stretch of a route.

Synthetic test-only stops; never real commuter guidance.
"""
from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from transit.models import NetworkDataVersion, PatternStop, Route, RoutePattern, RouteSegment, Stop

pytestmark = pytest.mark.django_db

URL = "/admin/transit/routepattern/"
# Out to a turnaround loop and back: the kept stop is "Church Stop".
NAMES = ["Start", "Mid", "Church Stop", "Loop A", "Loop B", "Loop C", "Return 1", "Return 2"]
KEEP, LAST = "Church Stop", "Loop C"


def _pattern(code="T9", names=NAMES):
    stops = Stop.objects.bulk_create([Stop(name=n, latitude=10.3 + i / 1000, longitude=123.9) for i, n in enumerate(names)])
    route = Route.objects.create(code=code, name=f"Test {code}", vehicle_class="jeepney")
    pattern = RoutePattern.objects.create(route=route, variant_key="v", direction="unspecified", status="documented")
    occ = PatternStop.objects.bulk_create(
        [PatternStop(pattern=pattern, stop=s, sequence=i, distance_along_m=i * 100) for i, s in enumerate(stops)])
    RouteSegment.objects.bulk_create(
        [RouteSegment(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=100) for a, b in zip(occ, occ[1:])])
    return pattern


@pytest.fixture
def staff(client):
    User.objects.create_superuser("owner-test", "o@example.com", "test-only-password")
    client.login(username="owner-test", password="test-only-password")
    return client


def _post(client, patterns, step, keep=KEEP, last=LAST, mode="off"):
    return client.post(URL, {"action": "adjust_stop_stretch", "step": step, "keep_stop": keep,
                             "last_stop": last, "mode": mode,
                             "_selected_action": [str(p.pk) for p in patterns]})


def _flags(pattern):
    return {o.stop.name: (o.can_board, o.can_alight)
            for o in pattern.pattern_stops.select_related("stop").order_by("sequence")}


def test_preview_lists_exactly_the_stretch_and_changes_nothing(staff):
    pattern = _pattern()
    page = _post(staff, [pattern], "preview").content.decode()
    for name in ("Loop A", "Loop B", "Loop C"):
        assert name in page
    for name in ("Start", "Church Stop", "Return 1"):
        assert f"<td>{name}</td>" not in page
    assert "Apply this change" in page
    assert all(flags == (True, True) for flags in _flags(pattern).values())


def test_apply_switches_off_only_that_stretch_and_keeps_the_road_data(staff):
    pattern = _pattern()
    version_before = NetworkDataVersion.objects.get_or_create(pk=1)[0].version
    response = _post(staff, [pattern], "apply")
    assert response.status_code == 302  # back to the list, with a "Done" message
    flags = _flags(pattern)
    assert {n for n, f in flags.items() if f == (False, False)} == {"Loop A", "Loop B", "Loop C"}
    assert flags["Church Stop"] == (True, True) and flags["Return 1"] == (True, True)
    assert RouteSegment.objects.filter(pattern=pattern).count() == len(NAMES) - 1  # segments untouched
    assert PatternStop.objects.filter(pattern=pattern).count() == len(NAMES)  # nothing deleted
    assert NetworkDataVersion.objects.get(pk=1).version > version_before  # planner reloads


def test_switching_back_on_restores_everything(staff):
    pattern = _pattern()
    _post(staff, [pattern], "apply")
    _post(staff, [pattern], "apply", mode="on")
    assert all(flags == (True, True) for flags in _flags(pattern).values())


def test_wrong_names_block_the_whole_change(staff):
    good, bad = _pattern("T1"), _pattern("T2", names=["A", "B", "C"])
    page = _post(staff, [good, bad], "apply").content.decode()
    assert "No stop named" in page
    assert all(flags == (True, True) for flags in _flags(good).values())  # nothing applied anywhere


def test_last_stop_must_come_after_the_kept_stop(staff):
    pattern = _pattern()
    page = _post(staff, [pattern], "preview", keep="Loop C", last="Start").content.decode()
    assert "does not come after the kept stop" in page


def test_only_a_logged_in_superuser_can_use_it(client):
    pattern = _pattern()
    assert _post(client, [pattern], "apply").status_code == 302  # sent to the login page
    assert all(flags == (True, True) for flags in _flags(pattern).values())
