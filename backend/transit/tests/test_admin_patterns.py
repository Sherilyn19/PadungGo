"""Route-pattern Admin stays usable on a large import and exports stored stops.

Synthetic test-only records; never real commuter guidance.
"""
from __future__ import annotations

import csv
import io

import pytest
from django.contrib.auth.models import User
from django.db import connection

from transit.models import PatternStop, Route, RoutePattern, RouteSegment, Stop

pytestmark = pytest.mark.django_db

CHANGE_URL = "/admin/transit/routepattern/{}/change/"
CHANGELIST_URL = "/admin/transit/routepattern/"


def _pattern(route, key, stops):
    pattern = RoutePattern.objects.create(route=route, variant_key=key, direction="unspecified",
                                          status="documented")
    occurrences = PatternStop.objects.bulk_create([
        PatternStop(pattern=pattern, stop=stop, sequence=i, distance_along_m=i * 100)
        for i, stop in enumerate(stops)
    ])
    RouteSegment.objects.bulk_create([
        RouteSegment(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=100)
        for a, b in zip(occurrences, occurrences[1:])
    ])
    return pattern


def _network(extra_patterns):
    stops = Stop.objects.bulk_create([
        Stop(name=f"Test Stop {i}", latitude=10.3, longitude=123.9 + i / 1000) for i in range(20)
    ])
    stops[0].name = "=Formula Stop"
    stops[0].save()
    route = Route.objects.create(code="T1", name="Test Route", vehicle_class="jeepney")
    first = _pattern(route, "gtfs:T1:dir0:1", stops)
    for n in range(extra_patterns):
        _pattern(route, f"extra-{n}", stops)
    return first


@pytest.fixture
def staff_client(client):
    User.objects.create_superuser("admin-test", "admin@example.com", "test-only-password")
    client.login(username="admin-test", password="test-only-password")
    return client


def _count_queries(callable_):
    count = [0]

    def counter(execute, sql, params, many, context):
        count[0] += 1
        return execute(sql, params, many, context)

    with connection.execute_wrapper(counter):
        response = callable_()
    return response, count[0]


def test_change_page_cost_does_not_grow_with_other_patterns(staff_client):
    small = _network(extra_patterns=0)
    _, small_queries = _count_queries(lambda: staff_client.get(CHANGE_URL.format(small.pk)))

    big_route = Route.objects.create(code="T2", name="Other", vehicle_class="jeepney")
    for n in range(5):
        _pattern(big_route, f"other-{n}", list(Stop.objects.all()))
    response, big_queries = _count_queries(lambda: staff_client.get(CHANGE_URL.format(small.pk)))

    assert response.status_code == 200
    # The first request also loads the session, so it may run one extra query.
    assert big_queries <= small_queries
    html = response.content.decode()
    assert "Test Stop 5" in html
    # Stops are displayed, not offered as dropdowns of every stop in the database.
    assert 'name="pattern_stops-0-stop"' not in html
    assert 'name="segments-0-from_occurrence"' not in html


def test_pattern_settings_can_still_be_saved(staff_client):
    pattern = _network(extra_patterns=0)
    page = staff_client.get(CHANGE_URL.format(pattern.pk))
    form = page.context["adminform"].form
    data = {name: form[name].value() or "" for name in form.fields if name != "geometry"}
    data["signboard"] = "Test signboard"
    for formset in page.context["inline_admin_formsets"]:
        management = formset.formset.management_form
        for name in management.fields:
            data[f"{management.prefix}-{name}"] = management[name].value()
        for index, inline_form in enumerate(formset.formset.forms):
            prefix = inline_form.prefix
            data[f"{prefix}-id"] = str(inline_form.instance.pk)
            data[f"{prefix}-pattern"] = str(pattern.pk)

    response = staff_client.post(CHANGE_URL.format(pattern.pk), data)

    assert response.status_code == 302
    pattern.refresh_from_db()
    assert pattern.signboard == "Test signboard"
    assert pattern.pattern_stops.count() == 20


def test_export_lists_documented_stops_in_order(staff_client):
    pattern = _network(extra_patterns=0)
    response = staff_client.post(CHANGELIST_URL, {
        "action": "export_ordered_stops", "_selected_action": [str(pattern.pk)],
    })

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(response.content.decode("utf-8-sig"))))
    assert [int(r["sequence"]) for r in rows] == list(range(20))
    assert rows[0]["pattern_status"] == "documented"
    assert rows[0]["variant_key"] == "gtfs:T1:dir0:1"
    assert rows[0]["stop_name"] == "'=Formula Stop"  # not run as a spreadsheet formula
    assert rows[0]["segment_to_next_m"] == "100"
    assert rows[-1]["segment_to_next_m"] == ""


def test_export_requires_admin_login(client):
    pattern = _network(extra_patterns=0)
    response = client.post(CHANGELIST_URL, {
        "action": "export_ordered_stops", "_selected_action": [str(pattern.pk)],
    })
    assert response.status_code == 302
    assert "/admin/login/" in response["Location"]
