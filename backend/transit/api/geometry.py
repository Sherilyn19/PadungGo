"""Attach sourced street geometry to ride segments of a planned response.

The planner network is loaded without geometry to save memory; after planning,
only the segments used by the returned rides are fetched. Geometry comes from
the imported route shapes (GTFS shapes.txt projected per stop segment). When a
segment has no stored shape, the ride's geometry stays null; no straight line
is invented.
"""
from __future__ import annotations

from transit.geocompat import linestring_coords
from transit.models import RouteSegment


def attach_ride_geometry(options: list[dict]) -> None:
    rides = [s for o in options for s in o["segments"] if s.get("mode") == "ride"]
    if not rides:
        return
    pattern_ids = {r["route_pattern_id"] for r in rides}
    rows = (
        RouteSegment.objects.filter(pattern_id__in=pattern_ids)
        .values_list("pattern_id", "from_occurrence__sequence", "geometry")
    )
    by_pattern: dict[str, dict[int, list]] = {}
    for pid, seq, geom in rows:
        by_pattern.setdefault(str(pid), {})[seq] = linestring_coords(geom)

    for ride in rides:
        segs = by_pattern.get(ride["route_pattern_id"], {})
        coords: list = []
        complete = True
        for seq in range(ride["board_sequence"], ride["alight_sequence"]):
            part = segs.get(seq)
            if not part:
                complete = False
                break
            coords.extend(part if not coords else part[1:])
        ride["geometry"] = (
            {"type": "LineString", "coordinates": coords} if complete and len(coords) >= 2 else None
        )
