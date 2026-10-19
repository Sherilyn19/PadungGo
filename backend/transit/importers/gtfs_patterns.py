"""Group scheduled trips and select patterns supported by usable shapes."""
from __future__ import annotations

from typing import Iterable, Optional

from .gtfs_geometry import project_stops
from .gtfs_types import FeedData, GTFSImportError, ImportReport

MAX_STOP_OFFSET_M = 150.0


def _parse_time(value: str) -> Optional[int]:
    if not value:
        return None
    try:
        hours, minutes, seconds = (int(part) for part in value.split(":"))
    except ValueError:
        return None
    return hours * 3600 + minutes * 60 + seconds


def _record_trip(trip_id, rows, trips, finished, patterns) -> None:
    if trip_id is None or trip_id not in trips:
        return
    if trip_id in finished:
        raise GTFSImportError("stop_times.txt must be grouped by trip_id.")
    finished.add(trip_id)
    rows.sort(key=lambda row: row[0])
    trip = trips[trip_id]
    key = (
        trip["route_id"],
        trip.get("direction_id", ""),
        tuple((row[1], row[4], row[5]) for row in rows),
    )
    entry = patterns.get(key)
    if entry is None:
        patterns[key] = {"trip": trip, "rows": rows, "trip_count": 1}
    else:
        entry["trip_count"] += 1
        # Keep the first representative unless a later trip supplies a shape.
        if not entry["trip"].get("shape_id") and trip.get("shape_id"):
            entry["trip"], entry["rows"] = trip, rows


def group_patterns(stop_times: Iterable[dict], trips: dict[str, dict]) -> dict:
    """Stream grouped stop times, retaining one representative per pattern."""
    patterns: dict[tuple, dict] = {}
    finished: set[str] = set()
    current_id, current = None, []

    for row in stop_times:
        trip_id = row["trip_id"]
        if trip_id != current_id:
            _record_trip(current_id, current, trips, finished, patterns)
            current_id, current = trip_id, []
        try:
            sequence = int(row["stop_sequence"])
        except (KeyError, ValueError):
            continue
        exact = row.get("timepoint", "1") != "0"
        current.append((
            sequence,
            row["stop_id"],
            _parse_time(row.get("arrival_time", "")) if exact else None,
            _parse_time(row.get("departure_time", "")) if exact else None,
            row.get("pickup_type", "0") != "1",
            row.get("drop_off_type", "0") != "1",
        ))
    _record_trip(current_id, current, trips, finished, patterns)
    return patterns


def _stop_coordinates(rows: list, stops: dict[str, dict]) -> Optional[list]:
    coordinates = []
    for row in rows:
        raw = stops.get(row[1])
        try:
            coordinates.append((float(raw["stop_lat"]), float(raw["stop_lon"])))
        except (TypeError, KeyError, ValueError):
            return None
    return coordinates


def select_patterns(feed: FeedData, report: ImportReport) -> list:
    """Keep patterns whose ordered stops can be projected near their shape."""
    accepted = []
    for key, entry in sorted(feed.patterns.items(), key=lambda item: (item[0][0], item[0][1])):
        trip, rows = entry["trip"], entry["rows"]
        if len(rows) < 2:
            report.skipped_too_short += 1
            continue
        shape = feed.shapes.get(trip.get("shape_id", ""))
        coordinates = _stop_coordinates(rows, feed.stops)
        projections = project_stops(shape, coordinates) if shape and coordinates else None
        if projections is None:
            report.skipped_no_shape += 1
            continue
        if max(projection.offset_m for projection in projections) > MAX_STOP_OFFSET_M:
            report.skipped_off_shape += 1
            continue
        accepted.append((key, entry, shape, projections))
    return accepted
