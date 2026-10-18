"""GTFS importer tests using a tiny in-memory feed (test-only, not real data)."""
from __future__ import annotations

import io
import zipfile

import pytest


from transit.importers.gtfs import GTFSImportError, ImportOptions, import_gtfs
from transit.models import PatternStop, Route, RoutePattern, Stop, TransferConnection
from transit.planner import PlanRequest, plan_journeys
from transit.planner.loader import load_network
from transit.planner.models import Endpoint

pytestmark = pytest.mark.django_db


def _csv(rows):
    return "\n".join(",".join(r) for r in rows) + "\n"


def _feed(*, with_shape=True) -> io.BytesIO:
    # Route X runs west->east along lat 10.30 through S1,S2,S3.
    # Route Y runs north from S3 to S4 (S3 is shared -> same-stop transfer).
    files = {
        "agency.txt": _csv([["agency_id", "agency_name", "agency_url", "agency_timezone"],
                            ["0", "Test Agency", "http://x", "Asia/Manila"]]),
        "routes.txt": _csv([["route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
                            ["X", "0", "TX", "Test X", "3"], ["Y", "0", "TY", "Test Y", "3"]]),
        "stops.txt": _csv([["stop_id", "stop_name", "stop_lat", "stop_lon"],
                           ["S1", "West", "10.3000", "123.9000"],
                           ["S2", "Middle", "10.3000", "123.9090"],
                           ["S3", "East Hub", "10.3000", "123.9180"],
                           ["S4", "North", "10.3090", "123.9180"]]),
        "trips.txt": _csv([["route_id", "service_id", "trip_id", "direction_id", "shape_id", "trip_headsign"],
                           ["X", "WK", "x1", "0", "shX" if with_shape else "", "To East"],
                           ["X", "WK", "x2", "0", "shX" if with_shape else "", "To East"],
                           ["Y", "WK", "y1", "0", "shY" if with_shape else "", "To North"]]),
        "stop_times.txt": _csv([
            ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
            ["x1", "08:00:00", "08:00:00", "S1", "1"], ["x1", "08:05:00", "08:05:00", "S2", "2"],
            ["x1", "08:10:00", "08:10:00", "S3", "3"],
            ["x2", "09:00:00", "09:00:00", "S1", "1"], ["x2", "09:05:00", "09:05:00", "S2", "2"],
            ["x2", "09:10:00", "09:10:00", "S3", "3"],
            ["y1", "08:20:00", "08:20:00", "S3", "1"], ["y1", "08:26:00", "08:26:00", "S4", "2"],
        ]),
        "shapes.txt": _csv([["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                            ["shX", "10.3000", "123.9000", "1"], ["shX", "10.3000", "123.9180", "2"],
                            ["shY", "10.3000", "123.9180", "1"], ["shY", "10.3090", "123.9180", "2"]]),
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in files.items():
            zf.writestr(name, text)
    buf.seek(0)
    return buf


def _opts(**kw):
    return ImportOptions(source_title="Test feed", source_reference="test://feed", **kw)


def test_import_creates_documented_directed_patterns():
    report = import_gtfs(_feed(), _opts())
    assert report.routes == 2 and report.patterns == 2  # x1/x2 identical -> one pattern
    assert set(RoutePattern.objects.values_list("status", flat=True)) == {"documented"}
    assert set(Stop.objects.values_list("status", flat=True)) == {"documented"}
    assert not RoutePattern.objects.filter(status="verified").exists()
    pat = RoutePattern.objects.get(route__code="TX")
    seqs = list(PatternStop.objects.filter(pattern=pat).order_by("sequence")
                .values_list("stop__name", "distance_along_m"))
    assert [s for s, _ in seqs] == ["West", "Middle", "East Hub"]
    # Distance along the shape: ~985 m per 0.009 deg lon at this latitude.
    assert 900 < seqs[1][1] < 1100 and 1800 < seqs[2][1] < 2100
    seg_times = sorted(pat.segments.values_list("riding_seconds", flat=True))
    assert seg_times == [300, 300]
    # Shared stop S3 -> one same-stop reboarding transfer.
    t = TransferConnection.objects.get()
    assert t.from_stop_id == t.to_stop_id and t.distance_m == 0


def test_patterns_without_shape_are_skipped_not_guessed():
    report = import_gtfs(_feed(with_shape=False), _opts())
    assert report.patterns == 0 and report.skipped_no_shape == 2
    assert Route.objects.count() == 0


def test_duplicate_import_rejected():
    import_gtfs(_feed(), _opts())
    with pytest.raises(GTFSImportError):
        import_gtfs(_feed(), _opts())


def test_bad_zip_rejected():
    with pytest.raises(GTFSImportError):
        import_gtfs(io.BytesIO(b"not a zip"), _opts())


def _plan(allow_documented):
    net = load_network(allow_documented=allow_documented, use_cache=False)
    req = PlanRequest(origin=Endpoint(latitude=10.3000, longitude=123.9000),
                      destination=Endpoint(latitude=10.3090, longitude=123.9180))
    return plan_journeys(net, req, config={"ALLOW_DOCUMENTED": allow_documented})


def test_documented_data_hidden_by_default():
    import_gtfs(_feed(), _opts())
    assert _plan(False).journey_options == []


def test_documented_data_planned_with_honest_labels_when_enabled():
    import_gtfs(_feed(), _opts())
    res = _plan(True)
    assert res.journey_options, res.warnings
    opt = res.journey_options[0]
    assert opt["transfers"] == 1
    assert [s["route_code"] for s in opt["segments"] if s["mode"] == "ride"] == ["TX", "TY"]
    assert opt["evidence"]["verification_status"] == "documented"
    assert any("not field-verified" in w for w in opt["warnings"])
    assert opt["fare"]["total_centavos"] is None  # no fares imported
    assert res.request_coverage_status == "limited_verified_coverage"
    # Reverse trip: patterns are directed, so no reversed journey.
    net = load_network(allow_documented=True, use_cache=False)
    back = plan_journeys(net, PlanRequest(origin=Endpoint(latitude=10.3090, longitude=123.9180),
                                          destination=Endpoint(latitude=10.3000, longitude=123.9000)),
                         config={"ALLOW_DOCUMENTED": True})
    assert back.journey_options == []


def test_admin_upload_page(admin_client):
    resp = admin_client.get("/admin/transit/datasource/import-gtfs/")
    assert resp.status_code == 200
    resp = admin_client.post("/admin/transit/datasource/import-gtfs/", {
        "feed": _upload(), "title": "Admin feed", "reference": "test://admin",
        "limitations": "test", "vehicle_class": "jeepney", "same_stop_transfers": "on",
    })
    assert resp.status_code == 200
    assert b"Imported 2 routes" in resp.content


def _upload():
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SimpleUploadedFile("feed.zip", _feed().getvalue(), content_type="application/zip")


def test_clean_stop_name():
    from transit.importers.gtfs import clean_stop_name

    assert clean_stop_name("M. Velez Street&(nodata)") == "M. Velez Street"
    assert clean_stop_name("(nodata)&(nodata)") == ""
    assert clean_stop_name("Osmena Boulevard&Osmena Boulevard") == "Osmena Boulevard"
    assert clean_stop_name("N. Escario Street&Gorordo Avenue") == "N. Escario Street & Gorordo Avenue"


def test_route_code_taken_from_route_id_when_short_name_is_descriptive():
    from transit.importers.gtfs import route_code_and_name

    # Shape of the Cebu DOTC archive: code in route_id, places in short_name.
    assert route_code_and_name({"route_id": "06F", "route_short_name": "GUADALUPE - CARBON - CAPITOL",
                                "route_long_name": ""}) == ("06F", "GUADALUPE - CARBON - CAPITOL")
    assert route_code_and_name({"route_id": "X", "route_short_name": "TX",
                                "route_long_name": "Test X"}) == ("TX", "Test X")


def test_api_plan_returns_street_geometry_for_imported_rides(client, settings):
    import json

    from transit.planner.loader import clear_network_cache

    import_gtfs(_feed(), _opts())
    settings.PLANNER = {**settings.PLANNER, "ALLOW_DOCUMENTED": True}
    clear_network_cache()
    resp = client.post("/api/v1/journeys/plan", content_type="application/json", data=json.dumps({
        "origin": {"latitude": 10.3000, "longitude": 123.9000},
        "destination": {"latitude": 10.3000, "longitude": 123.9180},
    }))
    assert resp.status_code == 200
    ride = next(s for s in resp.json()["journey_options"][0]["segments"] if s["mode"] == "ride")
    assert ride["geometry"]["type"] == "LineString"
    lon0, lat0 = ride["geometry"]["coordinates"][0]
    assert abs(lat0 - 10.30) < 0.001 and abs(lon0 - 123.90) < 0.001  # GeoJSON order
    walk = resp.json()["journey_options"][0]["segments"][0]
    assert walk["start"] == {"latitude": 10.3, "longitude": 123.9}
    assert walk["end"] == ride["start"]
