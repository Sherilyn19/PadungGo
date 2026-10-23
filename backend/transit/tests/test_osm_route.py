"""Adding stops at the start of a stored route from an OpenStreetMap route.

Synthetic test-only map data; never real commuter guidance.
"""
from __future__ import annotations

import json

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from transit.importers import osm_route as o
from transit.models import DataSource, NetworkDataVersion, PatternStop, Route, RoutePattern, RouteSegment, Stop

pytestmark = pytest.mark.django_db
URL = "/admin/transit/routepattern/"

# A straight east-to-west road split in two pieces drawn in opposite directions.
LON = [123.960, 123.955, 123.950, 123.945, 123.940, 123.935]
LAT = 10.330


def _way(lons):
    return [{"lat": LAT, "lon": lon} for lon in lons]


def _file(stop_names=("Far End", "Middle", "Church", "Meeting Point"), gap=False):
    stops = [(n, LON[i + 1]) for i, n in enumerate(stop_names)]  # Far End at 123.955 ...
    elements = [{"type": "relation", "id": 4242, "tags": {"ref": "ZZ9", "name": "Test line"}, "members": [
        {"type": "way", "ref": 1, "role": "", "geometry": _way(LON[:3] if not gap else LON[:2])},
        {"type": "way", "ref": 2, "role": "", "geometry": _way(list(reversed(LON[2:])))},  # drawn backwards
        *[{"type": "node", "ref": 100 + i, "role": "platform_entry_only" if i == 0 else "platform"} for i in range(len(stops))],
    ]}]
    elements += [{"type": "node", "id": 100 + i, "lat": LAT, "lon": lon, "tags": {"name": n}} for i, (n, lon) in enumerate(stops)]
    return json.dumps({"elements": elements}).encode()


def _stored_pattern(first_lon=LON[4], first_name="Old First"):
    names = [(first_name, first_lon, 300), ("Old Second", first_lon - 0.003, 900), ("Old Third", first_lon - 0.006, 1500)]
    stops = [Stop.objects.create(name=n, latitude=LAT, longitude=lon) for n, lon, _ in names]
    route = Route.objects.create(code="ZZ9", name="Stored", vehicle_class="jeepney")
    pattern = RoutePattern.objects.create(route=route, variant_key="v", direction="unspecified", status="documented")
    occ = [PatternStop.objects.create(pattern=pattern, stop=s, sequence=i, distance_along_m=d)
           for i, (s, (_, _, d)) in enumerate(zip(stops, names))]
    for a, b in zip(occ, occ[1:]):
        RouteSegment.objects.create(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=600)
    return pattern


def test_parse_follows_pieces_drawn_in_either_direction():
    route = o.parse_osm_route(_file())
    assert [s.name for s in route.stops] == ["Far End", "Middle", "Church", "Meeting Point"]
    assert route.stops[0].can_alight is False and route.stops[0].can_board is True  # entry only
    lons = [lon for _, lon in route.path]
    assert lons == sorted(lons, reverse=True)  # one continuous line, west to east


@pytest.mark.parametrize("raw,message", [
    (b"<html>busy</html>", "not an OpenStreetMap route"),
    (json.dumps({"elements": []}).encode(), "not an OpenStreetMap route"),
    (_file(gap=True), "gap"),
])
def test_bad_files_are_refused_in_plain_words(raw, message):
    with pytest.raises(o.OSMRouteError, match=message):
        o.parse_osm_route(raw)


def test_plan_measures_along_the_road_and_changes_nothing():
    pattern = _stored_pattern()
    plan = o.plan_extension(pattern, o.parse_osm_route(_file()), "Meeting Point")
    assert plan.problem == ""
    assert [n.stop.name for n in plan.new_stops] == ["Far End", "Middle", "Church"]
    assert plan.new_stops[0].along_m == 0
    assert all(n.hop_m > 300 for n in plan.new_stops)  # about 550 m per 0.005 degrees of longitude
    assert PatternStop.objects.filter(pattern=pattern).count() == 3


def test_apply_inserts_in_front_and_keeps_existing_distances():
    pattern = _stored_pattern()
    route = o.parse_osm_route(_file())
    plan = o.plan_extension(pattern, route, "Meeting Point")
    version = NetworkDataVersion.objects.get_or_create(pk=1)[0].version
    assert o.apply_extensions([plan], route) == 3

    rows = list(PatternStop.objects.filter(pattern=pattern).order_by("sequence").values_list("sequence", "stop__name", "distance_along_m"))
    assert [r[1] for r in rows] == ["Far End", "Middle", "Church", "Old First", "Old Second", "Old Third"]
    assert [r[0] for r in rows] == list(range(6))
    assert [r[2] for r in rows] == sorted(r[2] for r in rows)  # never goes backwards
    # old stops keep their spacing: only shifted
    assert rows[4][2] - rows[3][2] == 600 and rows[5][2] - rows[4][2] == 600
    segments = RouteSegment.objects.filter(pattern=pattern)
    assert segments.count() == 5
    assert sorted(segments.filter(from_occurrence__stop__name__startswith="Old").values_list("distance_m", flat=True)) == [600, 600]
    assert NetworkDataVersion.objects.get(pk=1).version > version
    source = Stop.objects.get(name="Far End").source
    assert source.license.startswith("ODbL") and source.title.startswith("OpenStreetMap route ZZ9")
    assert Stop.objects.get(name="Far End").status == "documented"


def test_two_routes_share_the_new_stops_and_second_run_is_refused():
    first, second = _stored_pattern(), _stored_pattern()
    second.route.code = "ZZ8"; second.route.save()
    route = o.parse_osm_route(_file())
    plans = [o.plan_extension(p, route, "Meeting Point") for p in (first, second)]
    o.apply_extensions(plans, route)
    assert Stop.objects.filter(name="Far End").count() == 1  # one shared stop, not two
    assert "already starts with stops from OpenStreetMap" in o.plan_extension(first, route, "Meeting Point").problem


@pytest.mark.parametrize("join,message", [
    ("Nowhere", "no stop named"),
    ("Far End", "nothing to add before"),
])
def test_wrong_join_stop(join, message):
    plan = o.plan_extension(_stored_pattern(), o.parse_osm_route(_file()), join)
    assert message in plan.problem


def test_routes_that_do_not_meet_are_refused():
    far = _stored_pattern(first_lon=123.990)
    assert "do not meet" in o.plan_extension(far, o.parse_osm_route(_file()), "Meeting Point").problem


@pytest.fixture
def staff(client):
    User.objects.create_superuser("owner-test", "o@example.com", "test-only-password")
    client.login(username="owner-test", password="test-only-password")
    return client


def _post(client, pattern, step, **extra):
    data = {"action": "extend_start_from_osm", "step": step, "join_stop": "Meeting Point",
            "_selected_action": [str(pattern.pk)], **extra}
    return client.post(URL, data)


def test_admin_preview_then_apply(staff):
    pattern = _stored_pattern()
    upload = SimpleUploadedFile("osm-route.json", _file(), content_type="application/json")
    page = _post(staff, pattern, "preview", route_file=upload).content.decode()
    assert "3 stops will be added" in page and "Far End" in page and "Apply this change" in page
    assert PatternStop.objects.filter(pattern=pattern).count() == 3  # preview saved nothing

    payload = page.split('name="payload" value="', 1)[1].split('"', 1)[0]
    import html
    response = _post(staff, pattern, "apply", payload=html.unescape(payload))
    assert response.status_code == 302
    assert PatternStop.objects.filter(pattern=pattern).count() == 6


def test_admin_shows_plain_error_for_a_bad_file(staff):
    pattern = _stored_pattern()
    upload = SimpleUploadedFile("x.json", b"<html>nope</html>")
    page = _post(staff, pattern, "preview", route_file=upload).content.decode()
    assert "not an OpenStreetMap route" in page and "background:#fdecea;color:#5c1410" in page


def test_only_a_superuser_can_apply(client):
    pattern = _stored_pattern()
    response = _post(client, pattern, "apply", payload=_file().decode())
    assert response.status_code == 302 and "/admin/login/" in response["Location"]
    assert PatternStop.objects.filter(pattern=pattern).count() == 3


def test_download_command_is_one_line_with_the_app_identity():
    command = o.download_command(3208066)
    assert "\n" not in command and "rel(3208066)" in command and o.OSMRouteError is not None
    assert "PadungGo/1.0" in command and "osm-route.json" in command
