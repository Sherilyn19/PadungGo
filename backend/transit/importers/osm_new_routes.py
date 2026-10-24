"""Create whole routes from routes mapped in OpenStreetMap.

Some places (for example parts of Lapu-Lapu and north Mandaue) have no stops in
the imported GTFS feed at all. When OpenStreetMap contributors have mapped a
route there (stops in order plus the road it follows), the route can be created
from that map data: its stops, the road distances between them and the road shape.

Honesty rules:
- Nothing is invented. Every stop, order and distance comes from the map file.
- Routes are stored as "documented", never "verified" (ODbL, credit OpenStreetMap contributors).
- A route code that already exists from another source is refused, so nothing is duplicated.
- Fares are not guessed: fares stay unknown until a verified fare rule names the route.

Staff download the routes as one file and upload it in Django Admin, because the
web server cannot reach the public Overpass service. Every change is previewed first.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from transit.geocompat import make_linestring, make_point
from transit.models import (
    DataSource, PatternStop, Route, RouteEvidence, RoutePattern, RouteSegment, Stop, TransferConnection,
)
from transit.models.enums import EvidenceStatus, RecordStatus
from transit.planner.loader import invalidate_network_cache

from .gtfs_geometry import project_stops, slice_shape
from .stop_links import apply_links, plan_links
from .osm_route import (
    LICENSE_TEXT, MAX_STOP_OFFSET_M, SOURCE_TITLE_PREFIX, MappedRoute, NewStop,
)

VARIANT_PREFIX = "osm:"
MIN_STOPS = 4
# Mapped routes that are not in the GTFS feed (checked against the live route list):
# 20A (Mandaue), MI-04A and MI-04B (Lapu-Lapu), 01K and 01Kx (to SM Seaside), 03L, 04B, 04H and 04M (Cebu City).
# Ones already imported are reported as "Already imported", so the list can be reused.
RECOMMENDED_RELATIONS = (
    3207109, 3207166, 20605536, 20605537, 20605538, 20605539, 20605540, 20605541,
    21251289, 21251290, 21452000, 21452001, 21251273, 21251274, 21251271, 21251272,
    21256982, 20587180, 20587181,
)
_DIRECTION_SUFFIX = re.compile(r"\s*\((?:in|out)bound\)\s*$", re.IGNORECASE)


def download_routes_command(relation_ids=RECOMMENDED_RELATIONS) -> str:
    """PowerShell command (Windows 10/11) that saves several OpenStreetMap routes as osm-routes.json."""
    ids = ",".join(str(int(i)) for i in relation_ids)
    return (
        "for ($i = 1; $i -le 5; $i++) { "
        "curl.exe -sS --fail --max-time 120 -A 'PadungGo/1.0 (+https://github.com/Sherilyn19/PadungGo)' "
        "-H 'Accept: application/json' "
        f"--data-urlencode 'data=[out:json][timeout:90];rel(id:{ids});out geom;node(r);out;' "
        "'https://overpass-api.de/api/interpreter' -o osm-routes.json; "
        "if ($LASTEXITCODE -eq 0) { break }; Start-Sleep -Seconds 15 }"
    )


@dataclass
class NewRoutePlan:
    route: MappedRoute
    stops: list = field(default_factory=list)      # NewStop; the first has hop_m 0 and no geometry
    pattern_path: list = field(default_factory=list)
    problem: str = ""

    @property
    def code(self) -> str:
        return self.route.ref.strip()

    @property
    def variant_key(self) -> str:
        return f"{VARIANT_PREFIX}{self.route.relation_id}"

    @property
    def last_stop_name(self) -> str:
        return self.stops[-1].stop.name if self.stops else ""

    @property
    def length_m(self) -> int:
        return self.stops[-1].along_m if self.stops else 0


def plan_new_route(route: MappedRoute) -> NewRoutePlan:
    """What would be created for one mapped route; nothing is saved."""
    plan = NewRoutePlan(route)
    if not plan.code:
        plan.problem = "This map route has no route code (ref), so it cannot be named."
        return plan
    if RoutePattern.objects.filter(variant_key=plan.variant_key).exists():
        plan.problem = "Already imported earlier; nothing to do."
        return plan
    # Same code from the GTFS feed means the route is already in the data.
    if RoutePattern.objects.filter(route__code=plan.code).exclude(variant_key__startswith=VARIANT_PREFIX).exists():
        plan.problem = f"Route {plan.code} already exists from another source, so it is not added again."
        return plan
    if len(route.stops) < MIN_STOPS:
        plan.problem = f"Only {len(route.stops)} mapped stops; at least {MIN_STOPS} are needed."
        return plan

    projections = project_stops(route.path, [(s.latitude, s.longitude) for s in route.stops])
    if projections is None:
        plan.problem = "The mapped road is too short to use."
        return plan
    far = next((s for s, p in zip(route.stops, projections) if p.offset_m > MAX_STOP_OFFSET_M), None)
    if far:
        plan.problem = f"Stop \u201c{far.name}\u201d is not on the mapped road, so the route looks inconsistent."
        return plan
    if projections[-1].along_m - projections[0].along_m < 300:
        plan.problem = "The stops are less than 300 m apart along the road, so the route looks wrong."
        return plan

    start = projections[0].along_m
    for i, (stop, here) in enumerate(zip(route.stops, projections)):
        if i == 0:
            plan.stops.append(NewStop(stop, 0, 0, []))
            continue
        before = projections[i - 1]
        plan.stops.append(NewStop(
            stop, round(here.along_m - start), max(0, round(here.along_m - before.along_m)),
            slice_shape(route.path, before, here),
        ))
    plan.pattern_path = slice_shape(route.path, projections[0], projections[-1])
    return plan


def _source_for_route(route: MappedRoute) -> DataSource:
    title = f"{SOURCE_TITLE_PREFIX} {route.ref or route.relation_id}: {route.name}"[:300]
    source, _ = DataSource.objects.get_or_create(
        title=title, reference=f"https://www.openstreetmap.org/relation/{route.relation_id}",
        defaults={"publisher": "OpenStreetMap contributors", "license": LICENSE_TEXT,
                  "collected_at": timezone.now(),
                  "limitations": "Mapped by OpenStreetMap contributors. Stops and road shape only; "
                                 "not field-verified and not proof of current service."})
    return source


def _stop_for(mapped, source: DataSource, by_osm_id: dict) -> Stop:
    """One saved stop per mapped stop, shared by every route that uses it (this is what makes transfers possible)."""
    if mapped.osm_id not in by_osm_id:
        stop = Stop.objects.filter(
            name=mapped.name, latitude=mapped.latitude, longitude=mapped.longitude,
            source__title__startswith=SOURCE_TITLE_PREFIX,
        ).first()
        by_osm_id[mapped.osm_id] = stop or Stop.objects.create(
            name=mapped.name, latitude=mapped.latitude, longitude=mapped.longitude,
            point=make_point(mapped.latitude, mapped.longitude), status=RecordStatus.DOCUMENTED, source=source)
    return by_osm_id[mapped.osm_id]


def _route_name(plans: list[NewRoutePlan]) -> str:
    names = []
    for plan in plans:
        name = _DIRECTION_SUFFIX.sub("", plan.route.name).strip()
        if name and name not in names:
            names.append(name)
    return " / ".join(names)[:200]


def _create_pattern(plan: NewRoutePlan, route: Route, source: DataSource, by_osm_id: dict) -> list[Stop]:
    pattern = RoutePattern.objects.create(
        route=route, variant_key=plan.variant_key, direction="unspecified",
        signboard=plan.route.name[:200], geometry=make_linestring(plan.pattern_path),
        status=RecordStatus.DOCUMENTED)
    stops = [_stop_for(n.stop, source, by_osm_id) for n in plan.stops]
    occurrences = PatternStop.objects.bulk_create([
        PatternStop(pattern=pattern, stop=stop, sequence=i, distance_along_m=n.along_m,
                    can_board=n.stop.can_board, can_alight=n.stop.can_alight)
        for i, (stop, n) in enumerate(zip(stops, plan.stops))])
    RouteSegment.objects.bulk_create([
        RouteSegment(pattern=pattern, from_occurrence=a, to_occurrence=b, distance_m=n.hop_m,
                     geometry=make_linestring(n.geometry), source=source)
        for a, b, n in zip(occurrences, occurrences[1:], plan.stops[1:])])
    RouteEvidence.objects.create(
        pattern=pattern, source=source, reviewed_at=timezone.now(), reviewer="automated OpenStreetMap import",
        status=EvidenceStatus.DOCUMENTED,
        notes="Stops and road shape from OpenStreetMap contributors; not field-verified.")
    return stops


def _add_same_stop_transfers(stops: list[Stop], source: DataSource) -> int:
    """Riding on, then changing to another route at the very same stop."""
    routes_at_stop: dict = {}
    for stop_id, route_id in (PatternStop.objects.filter(stop__in=stops)
                              .values_list("stop_id", "pattern__route_id").distinct()):
        routes_at_stop.setdefault(stop_id, set()).add(route_id)
    made = 0
    for stop in stops:
        if len(routes_at_stop.get(stop.id, ())) > 1:
            _, created = TransferConnection.objects.get_or_create(
                from_stop=stop, to_stop=stop,
                defaults={"distance_m": 0, "status": RecordStatus.DOCUMENTED, "source": source,
                          "restrictions": "Same mapped stop served by several routes; not a field-verified interchange."})
            made += created
    return made


@dataclass
class ImportResult:
    routes: int = 0
    patterns: int = 0
    stops: int = 0
    transfers: int = 0


def apply_new_routes(plans: list[NewRoutePlan], vehicle_class: str) -> ImportResult:
    """Create every plan, or none if anything fails."""
    result = ImportResult()
    ok = [p for p in plans if not p.problem]
    by_code: dict[str, list[NewRoutePlan]] = {}
    for plan in ok:
        by_code.setdefault(plan.code, []).append(plan)
    with transaction.atomic():
        by_osm_id: dict = {}
        all_stops: dict = {}
        first_source = None
        for code, group in by_code.items():
            route = Route.objects.filter(code=code, patterns__variant_key__startswith=VARIANT_PREFIX).first()
            if route is None:
                route = Route.objects.create(
                    code=code[:20], name=_route_name(group), vehicle_class=vehicle_class,
                    operator=group[0].route.operator[:200])
                result.routes += 1
            for plan in group:
                source = _source_for_route(plan.route)
                first_source = first_source or source
                for stop in _create_pattern(plan, route, source, by_osm_id):
                    all_stops[stop.id] = stop
                result.patterns += 1
        if first_source is not None:
            stops = list(all_stops.values())
            result.stops = len(stops)
            # Walking links to nearby stops already in the data, so riders can change onto existing routes.
            result.transfers = (_add_same_stop_transfers(stops, first_source)
                                + apply_links(plan_links({stop.id for stop in stops})))
        invalidate_network_cache()
    return result
