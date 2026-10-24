"""Walking links between nearby stops, so riders can change routes where they really do.

The imported feed only lets riders change routes at the very same stop. In real
life riders cross a street or walk to the next corner, so two stops of different
routes a short walk apart are never connected and good trips are missed.

This adds one-way links between stops that are close together. Nothing is
invented: the distance is the straight line between two stops already in the
data, the link is stored as "documented", and its note says the walking path is
not verified. Running it again adds nothing that exists already.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.utils import timezone

from transit.models import DataSource, PatternStop, Stop, TransferConnection
from transit.models.enums import RecordStatus
from transit.planner.geo import haversine_m
from transit.planner.loader import invalidate_network_cache

LINK_WALK_M = 150          # a short walk: about one street crossing or one block
LINKS_PER_STOP = 3         # only the nearest few, so the planner stays fast
_CELL_DEGREES = 0.0015     # about 165 m, so the 9 cells around a stop hold every stop within 150 m
SOURCE_TITLE = "PadungGo nearby-stop links"
RESTRICTIONS = "Straight-line distance between two stops; the walking path is not verified."


@dataclass(frozen=True)
class StopLink:
    from_stop_id: object
    to_stop_id: object
    from_name: str
    to_name: str
    distance_m: int


def plan_links(only_stop_ids: Optional[set] = None) -> list[StopLink]:
    """Links that are missing today. With `only_stop_ids`, only links touching those stops."""
    routes_at: dict = defaultdict(set)
    for stop_id, route_id in PatternStop.objects.values_list("stop_id", "pattern__route_id").distinct():
        routes_at[stop_id].add(route_id)
    stops = {s.id: s for s in Stop.objects.filter(id__in=routes_at.keys())}
    grid: dict = defaultdict(list)
    for stop in stops.values():
        grid[(int(stop.latitude // _CELL_DEGREES), int(stop.longitude // _CELL_DEGREES))].append(stop)
    existing = set(TransferConnection.objects.values_list("from_stop_id", "to_stop_id"))

    links: list[StopLink] = []
    for a in stops.values():
        row, col = int(a.latitude // _CELL_DEGREES), int(a.longitude // _CELL_DEGREES)
        found = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                for b in grid.get((row + dr, col + dc), ()):
                    if b.id == a.id or (a.id, b.id) in existing:
                        continue
                    if only_stop_ids is not None and a.id not in only_stop_ids and b.id not in only_stop_ids:
                        continue
                    # A link is only useful if the other stop offers a route this stop does not.
                    if not routes_at[b.id] - routes_at[a.id]:
                        continue
                    distance = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
                    if distance <= LINK_WALK_M:
                        found.append((distance, str(b.id), b))
        for distance, _, b in sorted(found, key=lambda item: item[:2])[:LINKS_PER_STOP]:
            links.append(StopLink(a.id, b.id, a.name, b.name, round(distance)))
    return links


def _source() -> DataSource:
    source, _ = DataSource.objects.get_or_create(
        title=SOURCE_TITLE, reference="https://github.com/Sherilyn19/PadungGo",
        defaults={"publisher": "PadungGo (computed from stop coordinates)", "license": "Computed; no outside data",
                  "collected_at": timezone.now(), "limitations": RESTRICTIONS})
    return source


def apply_links(links: list[StopLink]) -> int:
    """Save the links, all or none. Returns how many were added."""
    if not links:
        return 0
    with transaction.atomic():
        source = _source()
        TransferConnection.objects.bulk_create([
            TransferConnection(from_stop_id=l.from_stop_id, to_stop_id=l.to_stop_id, distance_m=l.distance_m,
                               status=RecordStatus.DOCUMENTED, source=source, restrictions=RESTRICTIONS)
            for l in links], ignore_conflicts=True)
        invalidate_network_cache()  # bulk_create sends no signals
    return len(links)
