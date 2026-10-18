"""
GTFS static feed importer.

Loads a published GTFS zip into the direction-aware schema with status
``documented`` (published/historic, NOT field-verified). It never marks anything
``verified``; promotion requires the seven-step review in docs/DATA_VERIFICATION.md.

What is imported, and how honestly:

* Routes  -> Route (code/name/operator from the feed; vehicle class from the
  feed text when it says jeepney/PUJ, otherwise the importer's stated default).
* Each distinct ordered stop sequence of a route+direction -> one RoutePattern.
  GTFS direction_id is not "outbound/inbound", so direction is ``unspecified``;
  the stop ORDER is still directed and enforced by the planner.
* Stop distances come from projecting stops onto the route shape (shapes.txt),
  i.e. distance along the actual street path. Patterns without a usable shape
  are skipped: straight-line stop distances are not used as ride distance.
* Ride times come from the scheduled stop_times of one representative trip
  (estimate_basis=schedule). Times flagged approximate (timepoint=0) -> unknown.
* Waiting stays unknown (frequencies are not converted into waits).
* Fares are NOT imported (GTFS fares are optional and would need verification).
* Transfers: explicit transfers.txt rows, plus optional same-stop reboarding
  where one GTFS stop is served by several routes (no walking is invented).

The feed file itself is not stored; only derived rows plus a DataSource record.
"""
from __future__ import annotations

import csv
import io
import math
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import IO, Iterable, Optional

from django.db import transaction
from django.utils import timezone

from transit.geocompat import make_linestring, make_point
from transit.models import (
    DataSource,
    EvidenceStatus,
    Location,
    PatternStop,
    RecordStatus,
    Route,
    RouteEvidence,
    RoutePattern,
    RouteSegment,
    Stop,
    TransferConnection,
)

MAX_STOP_OFFSET_M = 150.0  # stop farther than this from its shape => mismatch
_JEEPNEY_HINTS = ("jeep", "puj")


class GTFSImportError(Exception):
    pass


@dataclass
class ImportOptions:
    source_title: str
    source_reference: str = ""
    source_publisher: str = ""
    source_license: str = ""
    source_published_at: Optional[date] = None
    source_limitations: str = ""
    default_vehicle_class: str = "jeepney"
    same_stop_transfers: bool = True
    create_locations: bool = True


@dataclass
class ImportReport:
    routes: int = 0
    patterns: int = 0
    stops: int = 0
    locations: int = 0
    transfers: int = 0
    skipped_no_shape: int = 0
    skipped_off_shape: int = 0
    skipped_too_short: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Imported {self.routes} routes, {self.patterns} patterns, {self.stops} stops, "
            f"{self.transfers} transfers, {self.locations} locations (all 'documented'). "
            f"Skipped patterns: {self.skipped_no_shape} without a shape, "
            f"{self.skipped_off_shape} with stops off their shape, "
            f"{self.skipped_too_short} with fewer than 2 stops."
        )


# --- CSV helpers -----------------------------------------------------------


def _find(zf: zipfile.ZipFile, name: str) -> Optional[str]:
    for n in zf.namelist():
        if n.rsplit("/", 1)[-1] == name:
            return n
    return None


def _rows(zf: zipfile.ZipFile, name: str, required: bool = True) -> Iterable[dict]:
    member = _find(zf, name)
    if member is None:
        if required:
            raise GTFSImportError(f"GTFS file is missing {name}.")
        return iter(())
    raw = zf.open(member)
    text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
    return ({(k or "").strip(): (v or "").strip() for k, v in row.items()}
            for row in csv.DictReader(text))


def _parse_time(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        h, m, s = (int(x) for x in value.split(":"))
    except ValueError:
        return None
    return h * 3600 + m * 60 + s


# --- Geometry --------------------------------------------------------------


def _haversine(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class _Projection:
    index: int        # shape segment index
    t: float          # fraction along that segment
    along_m: float    # cumulative metres along the shape
    offset_m: float   # distance from stop to the shape
    lat: float
    lon: float


def _project_stops(shape: list[tuple[float, float]], stops: list[tuple[float, float]]):
    """Project ordered stops onto a shape, moving forward only.

    Returns a list of _Projection or None if the shape is unusable.
    """
    if len(shape) < 2:
        return None
    lat0 = shape[0][0]
    kx = 111_320.0 * math.cos(math.radians(lat0))
    ky = 110_540.0
    xy = [(lon * kx, lat * ky) for lat, lon in shape]
    cum = [0.0]
    for i in range(1, len(shape)):
        cum.append(cum[-1] + _haversine(*shape[i - 1], *shape[i]))

    out = []
    start = 0
    for lat, lon in stops:
        px, py = lon * kx, lat * ky
        cands = []
        for i in range(start, len(xy) - 1):
            (x1, y1), (x2, y2) = xy[i], xy[i + 1]
            dx, dy = x2 - x1, y2 - y1
            seg2 = dx * dx + dy * dy
            t = 0.0 if seg2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / seg2))
            qx, qy = x1 + t * dx, y1 + t * dy
            cands.append((math.hypot(px - qx, py - qy), i, t))
        if not cands:
            return None
        best = min(c[0] for c in cands)
        # Earliest candidate close to the best: avoids jumping ahead on loops.
        d, i, t = next(c for c in cands if c[0] <= best + 30.0)
        seg_len = cum[i + 1] - cum[i]
        plat = shape[i][0] + t * (shape[i + 1][0] - shape[i][0])
        plon = shape[i][1] + t * (shape[i + 1][1] - shape[i][1])
        along = cum[i] + t * seg_len
        if out and along < out[-1].along_m:
            along = out[-1].along_m
        out.append(_Projection(i, t, along, d, plat, plon))
        start = i
    return out


def _slice(shape, a: _Projection, b: _Projection) -> list[tuple[float, float]]:
    pts = [(a.lat, a.lon)]
    pts.extend(shape[a.index + 1: b.index + 1])
    pts.append((b.lat, b.lon))
    return pts


# --- Import ----------------------------------------------------------------


def _vehicle_class(route_row: dict, default: str) -> str:
    text = " ".join(route_row.get(k, "") for k in
                    ("route_short_name", "route_long_name", "route_desc")).lower()
    if any(h in text for h in _JEEPNEY_HINTS):
        return "jeepney"
    return default


def import_gtfs(fileobj: IO[bytes] | str, options: ImportOptions) -> ImportReport:
    """Import a GTFS zip (path or binary file object). Atomic: all or nothing."""
    try:
        zf = zipfile.ZipFile(fileobj)
    except zipfile.BadZipFile as exc:
        raise GTFSImportError("The uploaded file is not a valid GTFS zip.") from exc

    if options.source_reference and DataSource.objects.filter(
        reference=options.source_reference, title=options.source_title
    ).exists():
        raise GTFSImportError(
            "A data source with this title and reference was already imported. "
            "Delete it first in Django Admin if you really want to re-import."
        )

    with zf:
        agencies = {r.get("agency_id", ""): r.get("agency_name", "") for r in _rows(zf, "agency.txt", False)}
        routes = {r["route_id"]: r for r in _rows(zf, "routes.txt")}
        trips = {r["trip_id"]: r for r in _rows(zf, "trips.txt") if r.get("route_id") in routes}
        stops_raw = {r["stop_id"]: r for r in _rows(zf, "stops.txt")}

        # Stream stop_times; keep one representative trip per distinct pattern.
        patterns: dict[tuple, dict] = {}
        finished: set[str] = set()
        current_id, current = None, []

        def finish(trip_id, rows):
            if trip_id is None or trip_id not in trips:
                return
            if trip_id in finished:
                raise GTFSImportError("stop_times.txt must be grouped by trip_id.")
            finished.add(trip_id)
            rows.sort(key=lambda r: r[0])
            trip = trips[trip_id]
            key = (trip["route_id"], trip.get("direction_id", ""),
                   tuple((r[1], r[4], r[5]) for r in rows))
            entry = patterns.get(key)
            if entry is None:
                patterns[key] = {"trip": trip, "rows": rows, "trip_count": 1}
            else:
                entry["trip_count"] += 1
                if not entry["trip"].get("shape_id") and trip.get("shape_id"):
                    entry["trip"], entry["rows"] = trip, rows

        for r in _rows(zf, "stop_times.txt"):
            tid = r["trip_id"]
            if tid != current_id:
                finish(current_id, current)
                current_id, current = tid, []
            try:
                seq = int(r["stop_sequence"])
            except (KeyError, ValueError):
                continue
            exact = r.get("timepoint", "1") != "0"
            current.append((
                seq, r["stop_id"],
                _parse_time(r.get("arrival_time", "")) if exact else None,
                _parse_time(r.get("departure_time", "")) if exact else None,
                r.get("pickup_type", "0") != "1",     # can board
                r.get("drop_off_type", "0") != "1",   # can alight
            ))
        finish(current_id, current)

        needed_shapes = {p["trip"].get("shape_id") for p in patterns.values() if p["trip"].get("shape_id")}
        shapes: dict[str, list] = defaultdict(list)
        for r in _rows(zf, "shapes.txt", required=False):
            sid = r.get("shape_id")
            if sid in needed_shapes:
                try:
                    shapes[sid].append((int(r["shape_pt_sequence"]),
                                        float(r["shape_pt_lat"]), float(r["shape_pt_lon"])))
                except (KeyError, ValueError):
                    continue
        shape_pts = {sid: [(lat, lon) for _, lat, lon in sorted(pts)] for sid, pts in shapes.items()}

        transfer_rows = list(_rows(zf, "transfers.txt", required=False))

    report = ImportReport()

    # Pass 1 (in memory): decide which patterns are importable.
    accepted = []
    for key, entry in sorted(patterns.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        trip, rows = entry["trip"], entry["rows"]
        if len(rows) < 2:
            report.skipped_too_short += 1
            continue
        shape = shape_pts.get(trip.get("shape_id", ""))
        coords = []
        for r in rows:
            raw = stops_raw.get(r[1])
            try:
                coords.append((float(raw["stop_lat"]), float(raw["stop_lon"])))
            except (TypeError, KeyError, ValueError):
                coords = None
                break
        proj = _project_stops(shape, coords) if shape and coords else None
        if proj is None:
            report.skipped_no_shape += 1
            continue
        if max(p.offset_m for p in proj) > MAX_STOP_OFFSET_M:
            report.skipped_off_shape += 1
            continue
        accepted.append((key, entry, shape, proj))

    # Pass 2: bulk-write everything in one transaction (few round trips).
    with transaction.atomic():
        now = timezone.now()
        source = DataSource.objects.create(
            title=options.source_title,
            publisher=options.source_publisher,
            reference=options.source_reference,
            published_at=options.source_published_at,
            collected_at=now,
            license=options.source_license,
            limitations=options.source_limitations or (
                "Imported automatically from a published GTFS feed. Historic/published "
                "data: current operation, stops and directions are NOT field-verified."
            ),
        )

        stop_objs: dict[str, Stop] = {}
        for _, entry, _, _ in accepted:
            for r in entry["rows"]:
                gid = r[1]
                if gid in stop_objs:
                    continue
                raw = stops_raw[gid]
                lat, lon = float(raw["stop_lat"]), float(raw["stop_lon"])
                stop_objs[gid] = Stop(
                    name=(raw.get("stop_name") or gid)[:200], latitude=lat, longitude=lon,
                    point=make_point(lat, lon), status=RecordStatus.DOCUMENTED, source=source,
                )
        Stop.objects.bulk_create(stop_objs.values(), batch_size=1000)

        route_objs: dict[str, Route] = {}
        single_agency = next(iter(agencies.values())) if len(agencies) == 1 else ""
        for (route_id, _, _), _, _, _ in accepted:
            if route_id in route_objs:
                continue
            rrow = routes[route_id]
            route_objs[route_id] = Route(
                code=(rrow.get("route_short_name") or rrow.get("route_long_name") or route_id)[:20],
                name=(rrow.get("route_long_name") or "")[:200],
                vehicle_class=_vehicle_class(rrow, options.default_vehicle_class),
                operator=(agencies.get(rrow.get("agency_id", ""), "") or single_agency)[:200],
            )
        Route.objects.bulk_create(route_objs.values(), batch_size=1000)

        pattern_objs, occ_objs, seg_objs, ev_objs = [], [], [], []
        stop_routes: dict[str, set] = defaultdict(set)
        variant_counter: dict[tuple, int] = defaultdict(int)
        for (route_id, direction_id, _), entry, shape, proj in accepted:
            trip, rows = entry["trip"], entry["rows"]
            variant_counter[(route_id, direction_id)] += 1
            n = variant_counter[(route_id, direction_id)]
            pattern = RoutePattern(
                route=route_objs[route_id],
                variant_key=f"gtfs:{route_id}:dir{direction_id or 'x'}:{n}"[:100],
                direction="unspecified",
                signboard=(trip.get("trip_headsign") or "")[:200],
                geometry=make_linestring(_slice(shape, proj[0], proj[-1])),
                status=RecordStatus.DOCUMENTED,
            )
            pattern_objs.append(pattern)
            occs = []
            for seq, (r, p) in enumerate(zip(rows, proj)):
                occs.append(PatternStop(
                    pattern=pattern, stop=stop_objs[r[1]], sequence=seq,
                    distance_along_m=int(round(p.along_m)), can_board=r[4], can_alight=r[5],
                ))
                stop_routes[r[1]].add(route_id)
            occ_objs.extend(occs)
            for i in range(len(occs) - 1):
                a, b = rows[i], rows[i + 1]
                dep = a[3] if a[3] is not None else a[2]
                arr = b[2] if b[2] is not None else b[3]
                ride = arr - dep if dep is not None and arr is not None and arr >= dep else None
                seg_objs.append(RouteSegment(
                    pattern=pattern, from_occurrence=occs[i], to_occurrence=occs[i + 1],
                    distance_m=max(0, occs[i + 1].distance_along_m - occs[i].distance_along_m),
                    geometry=make_linestring(_slice(shape, proj[i], proj[i + 1])),
                    riding_seconds=ride, estimate_basis="schedule" if ride is not None else "",
                    source=source,
                ))
            ev_objs.append(RouteEvidence(
                pattern=pattern, source=source, reviewed_at=now,
                reviewer="automated GTFS import", status=EvidenceStatus.DOCUMENTED,
                notes=f"Representative of {entry['trip_count']} scheduled trip(s) in the feed.",
            ))
        RoutePattern.objects.bulk_create(pattern_objs, batch_size=500)
        PatternStop.objects.bulk_create(occ_objs, batch_size=2000)
        RouteSegment.objects.bulk_create(seg_objs, batch_size=1000)
        RouteEvidence.objects.bulk_create(ev_objs, batch_size=1000)
        report.routes, report.patterns, report.stops = len(route_objs), len(pattern_objs), len(stop_objs)

        # Transfers: explicit feed transfers, then optional same-stop reboarding.
        transfers: dict[tuple, TransferConnection] = {}
        for r in transfer_rows:
            if r.get("transfer_type") == "3":  # transfer not possible
                continue
            a, b = stop_objs.get(r.get("from_stop_id", "")), stop_objs.get(r.get("to_stop_id", ""))
            if not a or not b or (a.id, b.id) in transfers:
                continue
            mtt = r.get("min_transfer_time", "")
            transfers[(a.id, b.id)] = TransferConnection(
                from_stop=a, to_stop=b, distance_m=0 if a.id == b.id else None,
                duration_seconds=int(mtt) if mtt.isdigit() else None,
                restrictions="From the feed's transfers.txt; walking path not verified.",
                status=RecordStatus.DOCUMENTED, source=source,
            )
        if options.same_stop_transfers:
            for gid, rset in stop_routes.items():
                stop = stop_objs[gid]
                if len(rset) > 1 and (stop.id, stop.id) not in transfers:
                    transfers[(stop.id, stop.id)] = TransferConnection(
                        from_stop=stop, to_stop=stop, distance_m=0, duration_seconds=None,
                        restrictions=("Same-stop reboarding derived from the feed (stop served "
                                      "by several routes); not a field-verified interchange."),
                        status=RecordStatus.DOCUMENTED, source=source,
                    )
        TransferConnection.objects.bulk_create(transfers.values(), batch_size=1000)
        report.transfers = len(transfers)

        if options.create_locations:
            seen = set(Location.objects.values_list("name", flat=True))
            locs = []
            for stop in stop_objs.values():
                if stop.name in seen:
                    continue
                seen.add(stop.name)
                locs.append(Location(
                    name=stop.name, kind="place", latitude=stop.latitude,
                    longitude=stop.longitude, point=make_point(stop.latitude, stop.longitude),
                    status=RecordStatus.DOCUMENTED, source=source,
                ))
            Location.objects.bulk_create(locs, batch_size=1000)
            report.locations = len(locs)

    from transit.planner.loader import clear_network_cache
    clear_network_cache()
    return report
