"""Read GTFS CSV tables from an already checked archive."""
from __future__ import annotations

import csv
import io
import zipfile
from collections import defaultdict
from typing import Iterable, Optional

from .gtfs_patterns import group_patterns
from .gtfs_types import FeedData, GTFSImportError


def _find(zf: zipfile.ZipFile, name: str) -> Optional[str]:
    for member in zf.namelist():
        if member.rsplit("/", 1)[-1] == name:
            return member
    return None


def _rows(zf: zipfile.ZipFile, name: str, required: bool = True) -> Iterable[dict]:
    member = _find(zf, name)
    if member is None:
        if required:
            raise GTFSImportError(f"GTFS file is missing {name}.")
        return iter(())
    raw = zf.open(member)
    text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
    return (
        {(key or "").strip(): (value or "").strip() for key, value in row.items()}
        for row in csv.DictReader(text)
    )


def _read_shapes(zf: zipfile.ZipFile, patterns: dict) -> dict:
    needed_shapes = {
        entry["trip"].get("shape_id")
        for entry in patterns.values()
        if entry["trip"].get("shape_id")
    }
    shapes: dict[str, list] = defaultdict(list)
    for row in _rows(zf, "shapes.txt", required=False):
        shape_id = row.get("shape_id")
        if shape_id in needed_shapes:
            try:
                shapes[shape_id].append((
                    int(row["shape_pt_sequence"]),
                    float(row["shape_pt_lat"]),
                    float(row["shape_pt_lon"]),
                ))
            except (KeyError, ValueError):
                continue
    return {
        shape_id: [(lat, lon) for _, lat, lon in sorted(points)]
        for shape_id, points in shapes.items()
    }


def read_feed(zf: zipfile.ZipFile) -> FeedData:
    agencies = {
        row.get("agency_id", ""): row.get("agency_name", "")
        for row in _rows(zf, "agency.txt", False)
    }
    routes = {row["route_id"]: row for row in _rows(zf, "routes.txt")}
    trips = {
        row["trip_id"]: row
        for row in _rows(zf, "trips.txt")
        if row.get("route_id") in routes
    }
    stops = {row["stop_id"]: row for row in _rows(zf, "stops.txt")}
    patterns = group_patterns(_rows(zf, "stop_times.txt"), trips)
    shapes = _read_shapes(zf, patterns)
    transfer_rows = list(_rows(zf, "transfers.txt", required=False))
    return FeedData(
        agencies=agencies,
        routes=routes,
        stops=stops,
        patterns=patterns,
        shapes=shapes,
        transfer_rows=transfer_rows,
    )