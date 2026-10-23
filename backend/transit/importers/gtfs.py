"""
GTFS static feed importer.

Loads published feed records as documented, never field-verified. Ordered stop
patterns retain their direction; GTFS direction_id does not imply inbound or
outbound. Ride distances require sourced shapes, and approximate scheduled
times remain unknown. Fares and waiting times are not imported.

Writes derived rows and public source metadata, not the feed file itself.
"""
from __future__ import annotations

import re
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import IO

from django.db import transaction
from django.utils import timezone

from transit.geocompat import make_linestring, make_point
from transit.search_text import build_search_text
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

from .gtfs_feed import read_feed
from .gtfs_geometry import slice_shape
from .gtfs_patterns import MAX_STOP_OFFSET_M, select_patterns
from .gtfs_types import FeedData, GTFSImportError, ImportOptions, ImportReport

_JEEPNEY_HINTS = ("jeep", "puj")
_PLACEHOLDERS = {"", "(nodata)", "nodata", "name missing", "(name missing)"}
MAX_ARCHIVE_MEMBERS = 200  # a real GTFS feed has a few dozen files at most


@dataclass
class _PatternRows:
    patterns: list[RoutePattern] = field(default_factory=list)
    occurrences: list[PatternStop] = field(default_factory=list)
    segments: list[RouteSegment] = field(default_factory=list)
    evidence: list[RouteEvidence] = field(default_factory=list)
    stop_routes: dict[str, set] = field(default_factory=lambda: defaultdict(set))


def clean_stop_name(raw: str) -> str:
    """Tidy feed stop names like 'M. Velez Street&(nodata)'.

    Drops '(nodata)' parts and repeated halves; returns '' if nothing is left.
    """
    parts = []
    for part in (raw or "").split("&"):
        p = " ".join(part.split())
        if p.lower() in _PLACEHOLDERS or p in parts:
            continue
        parts.append(p)
    return " & ".join(parts)

def _real_text(raw: str | None) -> str:
    """Remove feed placeholders while preserving meaningful parenthetical names."""
    text = " ".join((raw or "").split())
    if text.lower() in _PLACEHOLDERS:
        return ""

    # Preserve real place names such as "(Ibabao)".
    text = re.sub(
        r"\s*\((?:name missing|nodata)\)$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    return "" if text.lower() in _PLACEHOLDERS else text


def route_code_and_name(row: dict) -> tuple[str, str]:
    """Choose a route code and name without mistaking a cleaned name for a code."""
    rid = (row.get("route_id") or "").strip()
    raw_short = " ".join((row.get("route_short_name") or "").split())
    short = _real_text(raw_short)
    long_ = _real_text(row.get("route_long_name"))

    # Classify the original field so cleaning a name cannot turn it into a code.
    if short and len(raw_short) <= 8 and " " not in raw_short:
        return short, long_

    name = long_ or short
    return (rid or short)[:20], name


def _vehicle_class(route_row: dict, default: str) -> str:
    text = " ".join(route_row.get(k, "") for k in
                    ("route_short_name", "route_long_name", "route_desc")).lower()
    if any(h in text for h in _JEEPNEY_HINTS):
        return "jeepney"
    return default


def _check_archive_limits(zf: zipfile.ZipFile) -> None:
    """Refuse archives that would expand to an unreasonable size (zip bombs).

    The sizes come from the zip directory. Python's zipfile stops reading a
    member at its declared size (and checks its CRC), so an archive cannot
    unpack to more than it declares here.
    """
    from django.conf import settings

    max_total = getattr(settings, "GTFS_MAX_UNCOMPRESSED_BYTES", 500 * 1024 * 1024)
    members = zf.infolist()
    if len(members) > MAX_ARCHIVE_MEMBERS:
        raise GTFSImportError("The zip contains too many files to be a GTFS feed.")
    if sum(m.file_size for m in members) > max_total:
        limit_mb = max_total // (1024 * 1024)
        raise GTFSImportError(f"The feed is larger than {limit_mb} MB once unzipped.")


def _reject_duplicate_source(options: ImportOptions) -> None:
    if options.source_reference and DataSource.objects.filter(
        reference=options.source_reference, title=options.source_title
    ).exists():
        raise GTFSImportError(
            "A data source with this title and reference was already imported. "
            "Delete it first in Django Admin if you really want to re-import."
        )


def _create_source(options: ImportOptions, now: datetime) -> DataSource:
    return DataSource.objects.create(
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


def _build_stops(accepted: list, feed: FeedData, source: DataSource) -> dict[str, Stop]:
    stops: dict[str, Stop] = {}
    for _, entry, _, _ in accepted:
        for row in entry["rows"]:
            stop_id = row[1]
            if stop_id in stops:
                continue
            raw = feed.stops[stop_id]
            lat, lon = float(raw["stop_lat"]), float(raw["stop_lon"])
            name = clean_stop_name(raw.get("stop_name", "")) or f"Unnamed stop (feed id {stop_id})"
            stops[stop_id] = Stop(
                name=name[:200], latitude=lat, longitude=lon,
                point=make_point(lat, lon), status=RecordStatus.DOCUMENTED, source=source,
            )
    return stops


def _build_routes(
    accepted: list, feed: FeedData, options: ImportOptions,
) -> dict[str, Route]:
    routes: dict[str, Route] = {}
    single_agency = next(iter(feed.agencies.values())) if len(feed.agencies) == 1 else ""
    for (route_id, _, _), _, _, _ in accepted:
        if route_id in routes:
            continue
        row = feed.routes[route_id]
        code, name = route_code_and_name(row)
        routes[route_id] = Route(
            code=code,
            name=name[:200],
            vehicle_class=_vehicle_class(row, options.default_vehicle_class),
            operator=(feed.agencies.get(row.get("agency_id", ""), "") or single_agency)[:200],
        )
    return routes


def _build_occurrences(
    pattern: RoutePattern, accepted_pattern: tuple,
    stops: dict[str, Stop], stop_routes: dict[str, set],
) -> list[PatternStop]:
    (route_id, _, _), entry, _, projections = accepted_pattern
    occurrences = []
    for sequence, (row, projection) in enumerate(zip(entry["rows"], projections)):
        occurrences.append(PatternStop(
            pattern=pattern, stop=stops[row[1]], sequence=sequence,
            distance_along_m=int(round(projection.along_m)),
            can_board=row[4], can_alight=row[5],
        ))
        stop_routes[row[1]].add(route_id)
    return occurrences


def _build_segments(
    pattern: RoutePattern, accepted_pattern: tuple,
    occurrences: list[PatternStop], source: DataSource,
) -> list[RouteSegment]:
    _, entry, shape, projections = accepted_pattern
    rows = entry["rows"]
    segments = []
    for i in range(len(occurrences) - 1):
        start, end = rows[i], rows[i + 1]
        departure = start[3] if start[3] is not None else start[2]
        arrival = end[2] if end[2] is not None else end[3]
        riding = (
            arrival - departure
            if departure is not None and arrival is not None and arrival >= departure
            else None
        )
        segments.append(RouteSegment(
            pattern=pattern,
            from_occurrence=occurrences[i],
            to_occurrence=occurrences[i + 1],
            distance_m=max(
                0, occurrences[i + 1].distance_along_m - occurrences[i].distance_along_m,
            ),
            geometry=make_linestring(slice_shape(shape, projections[i], projections[i + 1])),
            riding_seconds=riding,
            estimate_basis="schedule" if riding is not None else "",
            source=source,
        ))
    return segments


def _build_pattern_rows(
    accepted: list, stops: dict[str, Stop], routes: dict[str, Route],
    source: DataSource, now: datetime,
) -> _PatternRows:
    batch = _PatternRows()
    variant_counter: dict[tuple, int] = defaultdict(int)
    for accepted_pattern in accepted:
        (route_id, direction_id, _), entry, shape, projections = accepted_pattern
        trip = entry["trip"]
        variant_counter[(route_id, direction_id)] += 1
        number = variant_counter[(route_id, direction_id)]
        pattern = RoutePattern(
            route=routes[route_id],
            variant_key=f"gtfs:{route_id}:dir{direction_id or 'x'}:{number}"[:100],
            direction="unspecified",
            signboard=(trip.get("trip_headsign") or "")[:200],
            geometry=make_linestring(slice_shape(shape, projections[0], projections[-1])),
            status=RecordStatus.DOCUMENTED,
        )
        batch.patterns.append(pattern)
        occurrences = _build_occurrences(pattern, accepted_pattern, stops, batch.stop_routes)
        batch.occurrences.extend(occurrences)
        batch.segments.extend(_build_segments(pattern, accepted_pattern, occurrences, source))
        batch.evidence.append(RouteEvidence(
            pattern=pattern, source=source, reviewed_at=now,
            reviewer="automated GTFS import", status=EvidenceStatus.DOCUMENTED,
            notes=f"Representative of {entry['trip_count']} scheduled trip(s) in the feed.",
        ))
    return batch


def _build_explicit_transfers(
    rows: list[dict], stops: dict[str, Stop], source: DataSource,
) -> dict:
    transfers = {}
    for row in rows:
        if row.get("transfer_type") == "3":
            continue
        from_stop = stops.get(row.get("from_stop_id", ""))
        to_stop = stops.get(row.get("to_stop_id", ""))
        if not from_stop or not to_stop or (from_stop.id, to_stop.id) in transfers:
            continue
        minimum_time = row.get("min_transfer_time", "")
        transfers[(from_stop.id, to_stop.id)] = TransferConnection(
            from_stop=from_stop,
            to_stop=to_stop,
            distance_m=0 if from_stop.id == to_stop.id else None,
            duration_seconds=int(minimum_time) if minimum_time.isdigit() else None,
            restrictions="From the feed's transfers.txt; walking path not verified.",
            status=RecordStatus.DOCUMENTED,
            source=source,
        )
    return transfers


def _add_same_stop_transfers(
    transfers: dict, stops: dict[str, Stop],
    stop_routes: dict[str, set], source: DataSource,
) -> None:
    for stop_id, route_ids in stop_routes.items():
        stop = stops[stop_id]
        if len(route_ids) > 1 and (stop.id, stop.id) not in transfers:
            transfers[(stop.id, stop.id)] = TransferConnection(
                from_stop=stop, to_stop=stop, distance_m=0, duration_seconds=None,
                restrictions=(
                    "Same-stop reboarding derived from the feed (stop served "
                    "by several routes); not a field-verified interchange."
                ),
                status=RecordStatus.DOCUMENTED, source=source,
            )


def _build_locations(stops: dict[str, Stop], source: DataSource) -> list[Location]:
    seen = set(Location.objects.values_list("name", flat=True))
    locations = []
    for stop in stops.values():
        # Unnamed stops are not useful as searchable places.
        if stop.name.startswith("Unnamed stop") or stop.name in seen:
            continue
        seen.add(stop.name)
        locations.append(Location(
            name=stop.name, kind="place", latitude=stop.latitude,
            longitude=stop.longitude, point=make_point(stop.latitude, stop.longitude),
            # bulk_create skips save(), so fill the search words here.
            search_text=build_search_text(stop.name),
            status=RecordStatus.DOCUMENTED, source=source,
        ))
    return locations


def _write_feed(
    feed: FeedData, accepted: list, options: ImportOptions, report: ImportReport,
) -> None:
    # All imported rows succeed or roll back together.
    with transaction.atomic():
        now = timezone.now()
        source = _create_source(options, now)
        stops = _build_stops(accepted, feed, source)
        Stop.objects.bulk_create(stops.values(), batch_size=1000)
        routes = _build_routes(accepted, feed, options)
        Route.objects.bulk_create(routes.values(), batch_size=1000)

        batch = _build_pattern_rows(accepted, stops, routes, source, now)
        RoutePattern.objects.bulk_create(batch.patterns, batch_size=500)
        PatternStop.objects.bulk_create(batch.occurrences, batch_size=2000)
        RouteSegment.objects.bulk_create(batch.segments, batch_size=1000)
        RouteEvidence.objects.bulk_create(batch.evidence, batch_size=1000)
        report.routes, report.patterns, report.stops = len(routes), len(batch.patterns), len(stops)

        transfers = _build_explicit_transfers(feed.transfer_rows, stops, source)
        if options.same_stop_transfers:
            _add_same_stop_transfers(transfers, stops, batch.stop_routes, source)
        TransferConnection.objects.bulk_create(transfers.values(), batch_size=1000)
        report.transfers = len(transfers)

        if options.create_locations:
            locations = _build_locations(stops, source)
            Location.objects.bulk_create(locations, batch_size=1000)
            report.locations = len(locations)


def import_gtfs(fileobj: IO[bytes] | str, options: ImportOptions) -> ImportReport:
    """Import a GTFS zip (path or binary file object). Atomic: all or nothing."""
    try:
        zf = zipfile.ZipFile(fileobj)
    except zipfile.BadZipFile as exc:
        raise GTFSImportError("The uploaded file is not a valid GTFS zip.") from exc
    _check_archive_limits(zf)
    _reject_duplicate_source(options)

    with zf:
        feed = read_feed(zf)

    report = ImportReport()
    accepted = select_patterns(feed, report)
    _write_feed(feed, accepted, options, report)

    from transit.planner.loader import invalidate_network_cache
    invalidate_network_cache()
    return report
