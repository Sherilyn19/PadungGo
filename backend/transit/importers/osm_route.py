"""Extend the start or the end of an imported route with stops mapped in OpenStreetMap.

Some imported (GTFS) routes stop short of where jeepneys really start, or of
where they really end. When an OpenStreetMap contributor has mapped that route
(stops in order plus the road it follows), the missing first stops can be added
in front of the stored route, or the missing last stops after it. The
new stops, their road distances and the road shape all come from that map data
(ODbL, credit OpenStreetMap contributors). They are stored as "documented"
and are not field-verified.

Staff download one relation as a file and upload it in Django Admin, because
the web server cannot reach the public Overpass service. Nothing here runs on
its own: every change is previewed first and applied only after confirmation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from transit.geocompat import make_linestring, make_point
from transit.models import DataSource, PatternStop, RoutePattern, RouteSegment, Stop
from transit.models.enums import RecordStatus
from transit.planner.geo import haversine_m
from transit.planner.loader import invalidate_network_cache

from .gtfs_geometry import project_stops, slice_shape

MAX_FILE_BYTES = 5 * 1024 * 1024
# Pieces of road in the map data that do not touch are a sign of a broken route.
MAX_ROAD_GAP_M = 150
# A mapped stop this far from the mapped road does not belong to it.
MAX_STOP_OFFSET_M = 150
# The stored route's first stop must be this close to the stop where we join it.
MAX_JOIN_GAP_M = 300
# Sequence numbers are moved far away first so the unique (pattern, sequence) rule is never hit.
_SEQUENCE_PARKING = 100_000
LICENSE_TEXT = "ODbL 1.0 (© OpenStreetMap contributors)"
SOURCE_TITLE_PREFIX = "OpenStreetMap route"


def download_command(relation_id: int = 3208066) -> str:
    """PowerShell command (Windows 10/11) that saves one OpenStreetMap route as osm-route.json."""
    return (
        "for ($i = 1; $i -le 5; $i++) { "
        "curl.exe -sS --fail --max-time 120 -A 'PadungGo/1.0 (+https://github.com/Sherilyn19/PadungGo)' "
        "-H 'Accept: application/json' "
        f"--data-urlencode 'data=[out:json][timeout:60];rel({relation_id});out geom;node(r);out;' "
        "'https://overpass-api.de/api/interpreter' -o osm-route.json; "
        "if ($LASTEXITCODE -eq 0) { break }; Start-Sleep -Seconds 15 }"
    )


class OSMRouteError(Exception):
    """The message is safe to show to Admin staff."""


@dataclass
class MappedStop:
    osm_id: int
    name: str
    latitude: float
    longitude: float
    role: str

    @property
    def can_board(self) -> bool:
        return self.role != "platform_exit_only"

    @property
    def can_alight(self) -> bool:
        return self.role != "platform_entry_only"


@dataclass
class MappedRoute:
    relation_id: int
    ref: str
    name: str
    stops: list[MappedStop]
    path: list[tuple[float, float]]  # (lat, lon) along the road, in route order


def _join_ways(ways: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
    """Chain road pieces into one line, flipping pieces so their ends meet."""
    if len(ways) > 1:
        a, b = ways[0], ways[1]
        near = lambda p: min(haversine_m(*p, *b[0]), haversine_m(*p, *b[-1]))  # noqa: E731
        path = list(a) if near(a[-1]) <= near(a[0]) else list(reversed(a))
    else:
        path = list(ways[0])
    for way in ways[1:]:
        end = path[-1]
        piece = way if haversine_m(*end, *way[0]) <= haversine_m(*end, *way[-1]) else list(reversed(way))
        gap = haversine_m(*end, *piece[0])
        if gap > MAX_ROAD_GAP_M:
            raise OSMRouteError(f"The mapped road has a {gap:.0f} m gap, so it cannot be followed reliably.")
        path.extend(piece[1:] if gap < 1.0 else piece)
    return path


def parse_osm_route(raw: bytes) -> MappedRoute:
    """Read the file saved from the Overpass query `rel(ID);out geom;node(r);out;`."""
    if len(raw) > MAX_FILE_BYTES:
        raise OSMRouteError("That file is too large to be one route.")
    try:
        data = json.loads(raw)
        elements = data["elements"]
        relation = next(e for e in elements if e.get("type") == "relation")
    except (ValueError, KeyError, StopIteration, TypeError):
        raise OSMRouteError("This file is not an OpenStreetMap route. Download it again with the command shown.") from None
    if any(word in str(data.get("remark", "")).lower() for word in ("runtime error", "timed out")):
        raise OSMRouteError("The download was cut short by the server. Download it again.")

    nodes = {e["id"]: e for e in elements if e.get("type") == "node"}
    stops: list[MappedStop] = []
    ways: list[list[tuple[float, float]]] = []
    for member in relation.get("members", []):
        if member.get("type") == "node" and member.get("role", "").startswith(("platform", "stop")):
            node = nodes.get(member["ref"])
            if node:
                name = (node.get("tags") or {}).get("name") or f"Unnamed stop (OpenStreetMap {node['id']})"
                stops.append(MappedStop(node["id"], " ".join(name.split())[:200], node["lat"], node["lon"], member["role"]))
        elif member.get("type") == "way" and member.get("geometry"):
            ways.append([(p["lat"], p["lon"]) for p in member["geometry"]])
    if len(stops) < 2 or not ways:
        raise OSMRouteError("The route has no mapped stops or no mapped road.")
    tags = relation.get("tags") or {}
    return MappedRoute(relation["id"], tags.get("ref", ""), tags.get("name", ""), stops, _join_ways(ways))


@dataclass
class NewStop:
    stop: MappedStop
    # Start extension: metres from the first new stop; hop_m is the distance to the
    # next stop (or to the stored route start) and geometry runs to that next stop.
    # End extension: metres from the start of the stored route; hop_m is the distance
    # FROM the previous stop (or the stored route end) and geometry runs from it.
    along_m: int
    hop_m: int
    geometry: list


@dataclass
class ExtensionPlan:
    pattern: RoutePattern
    new_stops: list = field(default_factory=list)
    old_first_name: str = ""
    old_last_name: str = ""
    side: str = "start"   # "start" or "end"
    join_gap_m: int = 0
    shift_m: int = 0
    problem: str = ""

    @property
    def last_new_stop_name(self) -> str:
        return self.new_stops[-1].stop.name if self.new_stops else ""


def plan_extension(pattern: RoutePattern, route: MappedRoute, join_stop: str) -> ExtensionPlan:
    """What would be added in front of `pattern`; nothing is saved."""
    plan = ExtensionPlan(pattern)
    names = [s.name.casefold() for s in route.stops]
    wanted = join_stop.strip().casefold()
    if wanted not in names:
        plan.problem = f"The OpenStreetMap route has no stop named \u201c{join_stop.strip()}\u201d."
        return plan
    join_at = names.index(wanted)
    if join_at == 0:
        plan.problem = "That is the first stop of the OpenStreetMap route, so there is nothing to add before it."
        return plan

    projections = project_stops(route.path, [(s.latitude, s.longitude) for s in route.stops])
    if projections is None:
        plan.problem = "The mapped road is too short to use."
        return plan
    far = next((s for s, p in zip(route.stops, projections) if p.offset_m > MAX_STOP_OFFSET_M), None)
    if far:
        plan.problem = f"Stop \u201c{far.name}\u201d is not on the mapped road, so the route looks inconsistent."
        return plan

    first = pattern.pattern_stops.select_related("stop__source").order_by("sequence").first()
    if first is None:
        plan.problem = "This route has no stops."
        return plan
    plan.old_first_name = first.stop.name
    if first.stop.source_id and first.stop.source.title.startswith(SOURCE_TITLE_PREFIX):
        plan.problem = "This route already starts with stops from OpenStreetMap; nothing more to add."
        return plan
    join = route.stops[join_at]
    gap = haversine_m(join.latitude, join.longitude, first.stop.latitude, first.stop.longitude)
    if gap > MAX_JOIN_GAP_M:
        plan.problem = (f"\u201c{join.name}\u201d is {gap:.0f} m from this route's first stop "
                        f"(\u201c{first.stop.name}\u201d), so they do not meet.")
        return plan

    plan.join_gap_m = round(gap)
    first_along = projections[0].along_m
    for i in range(join_at):
        here, there = projections[i], projections[i + 1] if i + 1 <= join_at else projections[join_at]
        is_last = i == join_at - 1
        geometry = slice_shape(route.path, here, there)
        if is_last:
            geometry = geometry + [(first.stop.latitude, first.stop.longitude)]
        hop = round(there.along_m - here.along_m) + (plan.join_gap_m if is_last else 0)
        plan.new_stops.append(NewStop(route.stops[i], round(here.along_m - first_along), max(0, hop), geometry))
    last = plan.new_stops[-1]
    plan.shift_m = last.along_m + last.hop_m - first.distance_along_m
    return plan


def plan_end_extension(pattern: RoutePattern, route: MappedRoute, join_stop: str) -> ExtensionPlan:
    """What would be added after the last stop of `pattern`; nothing is saved.

    `join_stop` is the OpenStreetMap stop that sits next to the stored route's last
    stop. The stops AFTER it in the mapped route are added; the join stop itself is
    not (the stored last stop already stands for it).
    """
    plan = ExtensionPlan(pattern, side="end")
    names = [s.name.casefold() for s in route.stops]
    wanted = join_stop.strip().casefold()
    if wanted not in names:
        plan.problem = f"The OpenStreetMap route has no stop named \u201c{join_stop.strip()}\u201d."
        return plan
    join_at = names.index(wanted)
    if join_at == len(route.stops) - 1:
        plan.problem = "That is the last stop of the OpenStreetMap route, so there is nothing to add after it."
        return plan

    projections = project_stops(route.path, [(s.latitude, s.longitude) for s in route.stops])
    if projections is None:
        plan.problem = "The mapped road is too short to use."
        return plan
    far = next((s for s, p in zip(route.stops, projections) if p.offset_m > MAX_STOP_OFFSET_M), None)
    if far:
        plan.problem = f"Stop \u201c{far.name}\u201d is not on the mapped road, so the route looks inconsistent."
        return plan

    last = pattern.pattern_stops.select_related("stop__source").order_by("-sequence").first()
    if last is None:
        plan.problem = "This route has no stops."
        return plan
    plan.old_last_name = last.stop.name
    if last.stop.source_id and last.stop.source.title.startswith(SOURCE_TITLE_PREFIX):
        plan.problem = "This route already ends with stops from OpenStreetMap; nothing more to add."
        return plan
    join = route.stops[join_at]
    gap = haversine_m(join.latitude, join.longitude, last.stop.latitude, last.stop.longitude)
    if gap > MAX_JOIN_GAP_M:
        plan.problem = (f"\u201c{join.name}\u201d is {gap:.0f} m from this route's last stop "
                        f"(\u201c{last.stop.name}\u201d), so they do not meet.")
        return plan

    plan.join_gap_m = round(gap)
    along = last.distance_along_m
    for k in range(join_at + 1, len(route.stops)):
        here, there = projections[k - 1], projections[k]
        hop = max(0, round(there.along_m - here.along_m))
        geometry = slice_shape(route.path, here, there)
        if k == join_at + 1:
            hop += plan.join_gap_m
            geometry = [(last.stop.latitude, last.stop.longitude)] + geometry
        along += hop
        plan.new_stops.append(NewStop(route.stops[k], along, hop, geometry))
    return plan


def _source_for(route: MappedRoute) -> DataSource:
    title = f"{SOURCE_TITLE_PREFIX} {route.ref or route.relation_id}: {route.name}"[:300]
    reference = f"https://www.openstreetmap.org/relation/{route.relation_id}"
    source, created = DataSource.objects.get_or_create(
        title=title, reference=reference,
        defaults={"publisher": "OpenStreetMap contributors", "license": LICENSE_TEXT,
                  "collected_at": timezone.now(),
                  "limitations": "Mapped by OpenStreetMap contributors. Stops and road shape only; "
                                 "not field-verified and not proof of current service."})
    return source


def _stops_for(plans: list[ExtensionPlan], source: DataSource) -> dict[int, Stop]:
    """One saved stop per mapped stop, shared by every route that uses it."""
    stops_by_osm_id: dict[int, Stop] = {}
    for plan in plans:
        for new in plan.new_stops:
            if new.stop.osm_id not in stops_by_osm_id:
                stops_by_osm_id[new.stop.osm_id], _ = Stop.objects.get_or_create(
                    source=source, name=new.stop.name,
                    latitude=new.stop.latitude, longitude=new.stop.longitude,
                    defaults={"point": make_point(new.stop.latitude, new.stop.longitude),
                              "status": RecordStatus.DOCUMENTED})
    return stops_by_osm_id


def apply_end_extensions(plans: list[ExtensionPlan], route: MappedRoute) -> int:
    """Append every plan after the stored last stop, or none if anything fails.

    Existing stops, their sequence numbers and distances are not touched.
    Returns how many stops were added.
    """
    added = 0
    with transaction.atomic():
        source = _source_for(route)
        stops_by_osm_id = _stops_for(plans, source)
        for plan in plans:
            pattern = plan.pattern
            old_last = PatternStop.objects.filter(pattern=pattern).order_by("-sequence").first()
            occurrences = PatternStop.objects.bulk_create([
                PatternStop(pattern=pattern, stop=stops_by_osm_id[n.stop.osm_id], sequence=old_last.sequence + 1 + i,
                            distance_along_m=n.along_m, can_board=n.stop.can_board, can_alight=n.stop.can_alight)
                for i, n in enumerate(plan.new_stops)])
            RouteSegment.objects.bulk_create([
                RouteSegment(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=n.hop_m,
                             geometry=make_linestring(n.geometry), source=source)
                for a, b, n in zip([old_last] + occurrences, occurrences, plan.new_stops)])
            added += len(plan.new_stops)
        invalidate_network_cache()
    return added


def apply_extensions(plans: list[ExtensionPlan], route: MappedRoute) -> int:
    """Save every plan, or none if anything fails. Returns how many stops were added to patterns."""
    added = 0
    with transaction.atomic():
        source = _source_for(route)
        stops_by_osm_id = _stops_for(plans, source)
        for plan in plans:
            count = len(plan.new_stops)
            pattern = plan.pattern
            stored = PatternStop.objects.filter(pattern=pattern)
            # Two steps keep (pattern, sequence) unique at every moment.
            stored.update(sequence=F("sequence") + _SEQUENCE_PARKING)
            stored.update(sequence=F("sequence") - (_SEQUENCE_PARKING - count),
                          distance_along_m=F("distance_along_m") + plan.shift_m)
            old_first = PatternStop.objects.get(pattern=pattern, sequence=count)
            occurrences = PatternStop.objects.bulk_create([
                PatternStop(pattern=pattern, stop=stops_by_osm_id[n.stop.osm_id], sequence=i,
                            distance_along_m=n.along_m, can_board=n.stop.can_board, can_alight=n.stop.can_alight)
                for i, n in enumerate(plan.new_stops)])
            targets = occurrences[1:] + [old_first]
            RouteSegment.objects.bulk_create([
                RouteSegment(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=n.hop_m,
                             geometry=make_linestring(n.geometry), source=source)
                for a, b, n in zip(occurrences, targets, plan.new_stops)])
            added += count
        invalidate_network_cache()  # QuerySet.update() sends no signals
    return added
