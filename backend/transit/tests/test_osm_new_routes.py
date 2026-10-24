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


# --- walking links between nearby stops already in the data ---------------

def _route_with_stops(code, stops):
    from transit.models import PatternStop as PS
    route = Route.objects.create(code=code, name=code, vehicle_class="jeepney")
    pattern = RoutePattern.objects.create(route=route, variant_key=f"v-{code}", direction="unspecified", status="documented")
    for i, stop in enumerate(stops):
        PS.objects.create(pattern=pattern, stop=stop, sequence=i, distance_along_m=i * 500)


def test_nearby_stops_of_different_routes_are_linked_once():
    from transit.importers import stop_links as sl
    a = Stop.objects.create(name="A near", latitude=LAT, longitude=123.9500)
    a2 = Stop.objects.create(name="A end", latitude=LAT, longitude=123.9600)
    b = Stop.objects.create(name="B near", latitude=LAT + 0.0010, longitude=123.9500)   # about 110 m away
    b2 = Stop.objects.create(name="B end", latitude=LAT, longitude=123.9400)
    far = Stop.objects.create(name="B far", latitude=LAT + 0.004, longitude=123.9500)    # about 440 m away
    _route_with_stops("R1", [a, a2])
    _route_with_stops("R2", [b2, b, far])
    links = sl.plan_links()
    pairs = {(l.from_name, l.to_name) for l in links}
    assert pairs == {("A near", "B near"), ("B near", "A near")}
    assert all(100 < l.distance_m < 125 for l in links)
    assert sl.apply_links(links) == 2
    assert sl.plan_links() == []                      # running again adds nothing
    link = TransferConnection.objects.get(from_stop=a, to_stop=b)
    assert link.status == "documented" and "not verified" in link.restrictions


def test_stops_of_the_same_routes_are_not_linked():
    from transit.importers import stop_links as sl
    a = Stop.objects.create(name="Side one", latitude=LAT, longitude=123.9500)
    b = Stop.objects.create(name="Side two", latitude=LAT + 0.0005, longitude=123.9500)
    _route_with_stops("R3", [a, b])
    assert sl.plan_links() == []


def test_admin_previews_then_adds_links(staff):
    a = Stop.objects.create(name="A near", latitude=LAT, longitude=123.9500)
    b = Stop.objects.create(name="B near", latitude=LAT + 0.0010, longitude=123.9500)
    _route_with_stops("R1", [a])
    _route_with_stops("R2", [b])
    page = staff.get("/admin/transit/transferconnection/link-nearby-stops/").content.decode()
    assert "<strong>2</strong> links would be added" in page and TransferConnection.objects.count() == 0
    assert staff.post("/admin/transit/transferconnection/link-nearby-stops/", {"step": "apply"}).status_code == 302
    assert TransferConnection.objects.count() == 2


# --- routes typed in as a stop list ----------------------------------------
from transit.importers import stop_list as sl_mod  # noqa: E402

LIST_URL = "/admin/transit/route/import-stop-list/"
HEAD = "route_code,direction,stop_name,latitude,longitude\n"
GOOD = HEAD + "".join(f"QQ1,Town to Beach,Stop {i},10.30,{123.90 + i * 0.01}\n" for i in range(4))


def _list_plans(text):
    return [n.plan_new_route(r) for r in sl_mod.parse_stop_list(text)]


def test_a_typed_list_becomes_a_documented_route_with_straight_line_distances():
    plans = _list_plans(GOOD)
    assert plans[0].problem == "" and plans[0].code == "QQ1" and len(plans[0].stops) == 4
    n.apply_new_routes(plans, "jeepney")
    pattern = RoutePattern.objects.get(route__code="QQ1")
    assert pattern.status == "documented" and pattern.variant_key.startswith("list:QQ1:")
    assert RouteSegment.objects.filter(pattern=pattern).count() == 3
    assert 1000 < RouteSegment.objects.filter(pattern=pattern).first().distance_m < 1200
    assert "Stop list typed in" in pattern.evidence.first().source.title


def test_the_same_list_cannot_be_added_twice():
    n.apply_new_routes(_list_plans(GOOD), "jeepney")
    assert _list_plans(GOOD)[0].problem.startswith("Already imported")


def test_a_missing_direction_can_be_added_to_a_route_already_in_the_data():
    route = Route.objects.create(code="QQ1", name="From feed", vehicle_class="jeepney")
    RoutePattern.objects.create(route=route, variant_key="gtfs:qq1", direction="unspecified", status="documented")
    plans = _list_plans(GOOD)
    assert plans[0].problem == "" and plans[0].adds_to_existing
    n.apply_new_routes(plans, "jeepney")
    assert Route.objects.filter(code="QQ1").count() == 1 and RoutePattern.objects.filter(route=route).count() == 2


def test_two_directions_share_their_stops():
    back = HEAD + "".join(f"QQ1,Beach to Town,Stop {i},10.30,{123.90 + i * 0.01}\n" for i in (3, 2, 1, 0))
    n.apply_new_routes(_list_plans(GOOD + back.split("\n", 1)[1]), "jeepney")
    assert Stop.objects.filter(name="Stop 2").count() == 1 and RoutePattern.objects.count() == 2


def test_a_stop_without_coordinates_uses_one_exact_known_place_only():
    from transit.models import Location
    Location.objects.create(name="Unique Plaza", latitude=10.30, longitude=123.90, kind="place")
    Location.objects.create(name="Twin Plaza", latitude=10.30, longitude=123.91, kind="place")
    Location.objects.create(name="Twin Plaza", latitude=10.30, longitude=123.92, kind="place")
    rest = "".join(f"QQ2,Out,Stop {i},10.30,{123.93 + i * 0.01}\n" for i in range(3))
    assert _list_plans(HEAD + "QQ2,Out,unique plaza,,\n" + rest)[0].stops[0].stop.longitude == 123.90
    with pytest.raises(o.OSMRouteError, match="more than one known place"):
        sl_mod.parse_stop_list(HEAD + "QQ2,Out,Twin Plaza,,\n" + rest)
    with pytest.raises(o.OSMRouteError, match="no known place"):
        sl_mod.parse_stop_list(HEAD + "QQ2,Out,Nowhere Land,,\n" + rest)


@pytest.mark.parametrize("text,message", [
    ("wrong,header\n", "first line must be exactly"),
    (HEAD + "QQ3,Out,A,abc,123.9\n", "not a number"),
    (HEAD + "QQ3,Out,A,40.0,123.9\n", "outside Metro Cebu"),
    (HEAD + "QQ3,Out,A,10.30,123.90\nQQ3,Out,B,10.30,124.20\n", "wrong coordinate"),
    (HEAD + ",Out,A,10.30,123.90\n", "required"),
])
def test_bad_lists_are_refused_in_plain_words(text, message):
    with pytest.raises(o.OSMRouteError, match=message):
        sl_mod.parse_stop_list(text)


def test_admin_stop_list_preview_then_create(staff):
    page = staff.post(LIST_URL, {"step": "preview", "vehicle_class": "jeepney", "stop_list": GOOD}).content.decode()
    assert "Create these routes" in page and "Stop 2" in page and Route.objects.count() == 0
    payload = html.unescape(page.split('name="payload" value="', 1)[1].split('"', 1)[0])
    assert staff.post(LIST_URL, {"step": "apply", "vehicle_class": "jeepney", "payload": payload}).status_code == 302
    assert Route.objects.filter(code="QQ1").exists()


def test_admin_stop_list_shows_plain_error(staff):
    page = staff.post(LIST_URL, {"step": "preview", "stop_list": "nonsense"}).content.decode()
    assert "first line must be exactly" in page


def test_prefill_return_direction_writes_the_stops_backwards_and_the_list_then_imports(staff):
    route = Route.objects.create(code="RT9", name="Out and back", vehicle_class="jeepney")
    pattern = RoutePattern.objects.create(route=route, variant_key="gtfs:rt9", direction="unspecified", status="documented")
    for i in range(4):
        stop = Stop.objects.create(name=f"Stop, {i}", latitude=LAT, longitude=123.90 + i * 0.01)
        PatternStop.objects.create(pattern=pattern, stop=stop, sequence=i, distance_along_m=i * 1000)
    response = staff.post("/admin/transit/routepattern/", {"action": "prefill_return_direction", "_selected_action": [str(pattern.pk)]})
    assert response.status_code == 302 and response["Location"].endswith("/import-stop-list/")
    page = staff.get(LIST_URL).content.decode()
    assert page.index("Stop, 3") < page.index("Stop, 0") and "Out and back (return)" in page
    assert "Stop, 3" not in staff.get(LIST_URL).content.decode()         # shown once only
    text = html.unescape(page.split('rows="14"', 1)[1].split(">", 1)[1].split("</textarea>", 1)[0]).strip()
    plans = _list_plans(text)
    assert plans[0].problem == "" and plans[0].adds_to_existing and plans[0].stops[0].stop.name == "Stop, 3"
