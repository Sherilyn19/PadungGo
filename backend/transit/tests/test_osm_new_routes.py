"""Creating whole routes from OpenStreetMap map data.

Synthetic test-only map data; never real commuter guidance.
"""
from __future__ import annotations

import html
import json

import pytest
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile

from transit.importers import osm_new_routes as n
from transit.importers import osm_route as o
from transit.models import PatternStop, Route, RoutePattern, RouteSegment, Stop, TransferConnection

pytestmark = pytest.mark.django_db
URL = "/admin/transit/route/import-osm-routes/"
LAT = 10.330
LONS = [123.940, 123.945, 123.950, 123.955, 123.960]


def _relation(rel_id, ref, name, stop_ids, lons=LONS):
    return {"type": "relation", "id": rel_id, "tags": {"ref": ref, "name": name, "operator": "Test Coop"}, "members": [
        {"type": "way", "ref": rel_id, "role": "", "geometry": [{"lat": LAT, "lon": x} for x in lons]},
        *[{"type": "node", "ref": sid, "role": "platform"} for sid in stop_ids],
    ]}


def _nodes(names_by_id, lons=LONS):
    return [{"type": "node", "id": sid, "lat": LAT, "lon": lons[i], "tags": {"name": name}}
            for i, (sid, name) in enumerate(names_by_id.items())]


def _file(*relations_and_nodes):
    return json.dumps({"elements": list(relations_and_nodes)}).encode()


def _two_routes():
    """Route AA1 runs A-B-C-D-E; route BB2 runs B-C-D-E on the same road, so those stops are shared."""
    names = {1: "Stop A", 2: "Stop B", 3: "Stop C", 4: "Stop D", 5: "Stop E"}
    return _file(
        _relation(900, "AA1", "Alpha line (outbound)", [1, 2, 3, 4, 5]),
        _relation(901, "BB2", "Beta line", [2, 3, 4, 5], lons=LONS[1:]),   # reuses the same map points
        *_nodes(names),
    )


def _plans(raw):
    routes, skipped = o.parse_osm_routes(raw)
    return [n.plan_new_route(r) for r in routes], skipped


def test_plan_measures_along_the_road_and_saves_nothing():
    plans, skipped = _plans(_two_routes())
    first = plans[0]
    assert skipped == [] and first.problem == "" and first.code == "AA1"
    assert [s.stop.name for s in first.stops] == ["Stop A", "Stop B", "Stop C", "Stop D", "Stop E"]
    assert first.stops[0].along_m == 0 and first.stops[0].hop_m == 0
    assert [s.along_m for s in first.stops] == sorted(s.along_m for s in first.stops)
    assert 2100 < first.length_m < 2300        # 0.02 degrees of longitude, about 2.2 km at this latitude
    assert Route.objects.count() == 0 and Stop.objects.count() == 0


def test_apply_creates_documented_routes_and_shares_stops():
    plans, _ = _plans(_two_routes())
    result = n.apply_new_routes([p for p in plans if not p.problem], "jeepney")
    assert result.routes == 2 and result.patterns == 2
    route = Route.objects.get(code="AA1")
    assert route.name == "Alpha line" and route.vehicle_class == "jeepney" and route.operator == "Test Coop"
    pattern = RoutePattern.objects.get(route=route)
    assert pattern.status == "documented" and pattern.variant_key == "osm:900" and pattern.direction == "unspecified"
    assert PatternStop.objects.filter(pattern=pattern).count() == 5
    assert RouteSegment.objects.filter(pattern=pattern).count() == 4
    assert Stop.objects.filter(name="Stop C").count() == 1        # one stop shared by both routes
    assert all(s.status == "documented" for s in Stop.objects.all())
    shared = Stop.objects.get(name="Stop C")
    assert TransferConnection.objects.filter(from_stop=shared, to_stop=shared, distance_m=0).exists()


def test_a_second_import_adds_nothing():
    plans, _ = _plans(_two_routes())
    n.apply_new_routes([p for p in plans if not p.problem], "jeepney")
    again, _ = _plans(_two_routes())
    assert all(p.problem.startswith("Already imported") for p in again)
    assert n.apply_new_routes(again, "jeepney").patterns == 0
    assert RoutePattern.objects.count() == 2


def test_a_route_that_exists_from_another_source_is_not_duplicated():
    route = Route.objects.create(code="AA1", name="From GTFS", vehicle_class="jeepney")
    RoutePattern.objects.create(route=route, variant_key="gtfs:1", direction="unspecified", status="documented")
    plans, _ = _plans(_two_routes())
    assert "already exists from another source" in plans[0].problem
    assert plans[1].problem == ""
    n.apply_new_routes(plans, "jeepney")
    assert RoutePattern.objects.filter(route__code="AA1").count() == 1   # only the GTFS one


def test_several_directions_with_one_code_become_one_route():
    names = {1: "Stop A", 2: "Stop B", 3: "Stop C", 4: "Stop D", 5: "Stop E"}
    raw = _file(_relation(910, "CC3", "Gamma line (inbound)", [5, 4, 3, 2, 1], lons=list(reversed(LONS))),
                _relation(911, "CC3", "Gamma line (outbound)", [1, 2, 3, 4, 5]), *_nodes(names))
    plans, _ = _plans(raw)
    result = n.apply_new_routes(plans, "jeepney")
    assert result.routes == 1 and result.patterns == 2
    assert Route.objects.get(code="CC3").name == "Gamma line"


def test_new_stops_get_walking_links_to_stops_already_in_the_data():
    old_route = Route.objects.create(code="OLD", name="Old", vehicle_class="jeepney")
    old_pattern = RoutePattern.objects.create(route=old_route, variant_key="gtfs:old", direction="unspecified",
                                              status="documented")
    old_stop = Stop.objects.create(name="Old Stop", latitude=LAT + 0.0003, longitude=LONS[2])  # about 33 m away
    far_stop = Stop.objects.create(name="Far Old Stop", latitude=LAT + 0.01, longitude=LONS[2])
    for i, stop in enumerate((old_stop, far_stop)):
        PatternStop.objects.create(pattern=old_pattern, stop=stop, sequence=i, distance_along_m=i * 1000)
    plans, _ = _plans(_two_routes())
    n.apply_new_routes(plans, "jeepney")
    new_c = Stop.objects.get(name="Stop C")
    there = TransferConnection.objects.get(from_stop=new_c, to_stop=old_stop)
    back = TransferConnection.objects.get(from_stop=old_stop, to_stop=new_c)
    assert 20 < there.distance_m < 50 and back.distance_m == there.distance_m
    assert not TransferConnection.objects.filter(to_stop=far_stop).exists()   # too far to walk


@pytest.mark.parametrize("make,message", [
    (lambda: _file(_relation(920, "", "No code", [1, 2, 3, 4]), *_nodes({1: "A", 2: "B", 3: "C", 4: "D"})), "no route code"),
    (lambda: _file(_relation(921, "DD4", "Too few", [1, 2, 3]), *_nodes({1: "A", 2: "B", 3: "C"})), "at least 4"),
])
def test_unusable_routes_are_refused_in_plain_words(make, message):
    plans, _ = _plans(make())
    assert message in plans[0].problem


def test_a_stop_off_the_road_makes_the_route_inconsistent():
    nodes = _nodes({1: "A", 2: "B", 3: "C", 4: "D"})
    nodes[2]["lat"] += 0.01     # about 1.1 km from the road
    plans, _ = _plans(_file(_relation(922, "EE5", "Odd", [1, 2, 3, 4]), *nodes))
    assert "is not on the mapped road" in plans[0].problem


def test_a_broken_route_is_skipped_not_fatal():
    broken = _relation(930, "FF6", "Broken", [1, 2, 3, 4], lons=LONS[:2])
    broken["members"].insert(1, {"type": "way", "ref": 99, "role": "", "geometry": [
        {"lat": LAT + 0.1, "lon": 123.9}, {"lat": LAT + 0.1, "lon": 123.91}]})
    names = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E"}
    routes, skipped = o.parse_osm_routes(_file(broken, _relation(931, "GG7", "Good", [1, 2, 3, 4, 5]), *_nodes(names)))
    assert [r.ref for r in routes] == ["GG7"] and "FF6" in skipped[0] and "gap" in skipped[0]


def test_imported_routes_are_reachable_for_the_planner():
    from transit.planner.loader import load_network
    plans, _ = _plans(_two_routes())
    n.apply_new_routes(plans, "jeepney")
    network = load_network(allow_documented=True, use_cache=False)
    codes = {network.routes[p.route_id].code for p in network.patterns}
    assert {"AA1", "BB2"} <= codes


def test_download_command_lists_every_route_and_has_the_app_identity():
    command = n.download_routes_command((1, 2, 3))
    assert "rel(id:1,2,3)" in command and "PadungGo/1.0" in command and "\n" not in command


@pytest.fixture
def staff(client):
    User.objects.create_superuser("owner-test", "o@example.com", "test-only-password")
    client.login(username="owner-test", password="test-only-password")
    return client


def test_admin_preview_then_create(staff):
    upload = SimpleUploadedFile("osm-routes.json", _two_routes(), content_type="application/json")
    page = staff.post(URL, {"step": "preview", "vehicle_class": "jeepney", "routes_file": upload}).content.decode()
    assert "Create these routes" in page and "Stop A" in page and "AA1" in page
    assert Route.objects.count() == 0          # a preview saves nothing
    payload = html.unescape(page.split('name="payload" value="', 1)[1].split('"', 1)[0])
    response = staff.post(URL, {"step": "apply", "vehicle_class": "jeepney", "payload": payload})
    assert response.status_code == 302 and Route.objects.count() == 2


def test_admin_shows_plain_error_for_a_bad_file(staff):
    upload = SimpleUploadedFile("osm-routes.json", b"not json", content_type="application/json")
    page = staff.post(URL, {"step": "preview", "routes_file": upload}).content.decode()
    assert "not an OpenStreetMap route" in page


def test_only_a_superuser_can_use_it(client):
    User.objects.create_user("plain-staff", password="test-only-password", is_staff=True)
    client.login(username="plain-staff", password="test-only-password")
    assert client.post(URL, {"step": "preview"}).status_code in (302, 403)
    assert Route.objects.count() == 0


def test_change_list_links_to_the_tool(staff):
    assert "Add routes from OpenStreetMap" in staff.get("/admin/transit/route/").content.decode()
