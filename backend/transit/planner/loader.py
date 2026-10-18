"""
ORM -> planner dataclass loader. The ONLY planner module that touches Django.

Builds an in-memory Network from the database for a bounded geographic window so
the pure-Python engine can run. Keeps spatial access minimal and backend-agnostic
(works in both PostGIS and lite/SQLite modes).
"""
from __future__ import annotations

from typing import Iterable, Optional

from transit.models import (
    DataSource,
    FareRule,
    Location,
    PatternStop,
    Route,
    RouteEvidence,
    RoutePattern,
    RouteSegment,
    Stop,
    TransferConnection,
)
from transit.planner.models import (
    FarePolicy,
    Network,
    PatternData,
    PatternStopData,
    RouteData,
    SegmentData,
    StopData,
    TransferData,
)


def _statuses(allow_documented: bool) -> set[str]:
    return {"verified", "documented"} if allow_documented else {"verified"}


_CACHE: dict[bool, tuple[float, Network]] = {}
_CACHE_TTL_S = 300.0


def clear_network_cache() -> None:
    """Drop the cached network (call after imports or admin edits)."""
    _CACHE.clear()


def load_network(*, allow_documented: bool = False, use_cache: bool = True) -> Network:
    """Load the routable network, cached in-process for a few minutes.

    Only public, non-personal route data is cached. Admin saves and imports
    clear the cache.
    """
    import time

    now = time.monotonic()
    hit = _CACHE.get(allow_documented)
    if use_cache and hit and now - hit[0] < _CACHE_TTL_S:
        return hit[1]
    net = _load_network(allow_documented)
    _CACHE[allow_documented] = (now, net)
    return net


def _load_network(allow_documented: bool) -> Network:
    net = Network()
    statuses = _statuses(allow_documented)

    # Sources (public evidence references only).
    for src in DataSource.objects.all():
        net.sources[str(src.id)] = {
            "id": str(src.id),
            "title": src.title,
            "publisher": src.publisher,
            "reference": src.reference,
            "published_at": src.published_at.isoformat() if src.published_at else None,
            "license": src.license,
        }

    # values() queries: no model instances and no geometry columns, so a
    # city-sized network fits in the free plan's memory.
    for row in Stop.objects.values_list(
        "id", "name", "latitude", "longitude", "can_board", "can_alight", "status"
    ).iterator(chunk_size=2000):
        sid = str(row[0])
        net.stops[sid] = StopData(
            id=sid, name=row[1], latitude=row[2], longitude=row[3],
            can_board=row[4], can_alight=row[5], status=row[6],
        )

    for row in Route.objects.filter(active=True).values_list(
        "id", "code", "name", "vehicle_class", "operator"
    ):
        rid = str(row[0])
        net.routes[rid] = RouteData(
            id=rid, code=row[1], name=row[2], vehicle_class=row[3], operator=row[4] or None,
        )

    pattern_rows = list(
        RoutePattern.objects.filter(status__in=statuses, route__active=True).values_list(
            "id", "route_id", "direction", "variant_key", "signboard", "status", "verified_at"
        )
    )
    pattern_ids = [r[0] for r in pattern_rows]

    occ_by_pattern: dict = {}
    for row in PatternStop.objects.filter(pattern_id__in=pattern_ids).values_list(
        "pattern_id", "id", "stop_id", "sequence", "distance_along_m", "can_board", "can_alight"
    ).order_by("pattern_id", "sequence").iterator(chunk_size=5000):
        occ_by_pattern.setdefault(row[0], []).append(PatternStopData(
            id=str(row[1]), stop_id=str(row[2]), sequence=row[3],
            distance_along_m=row[4], can_board=row[5], can_alight=row[6],
        ))

    seg_by_pattern: dict = {}
    for row in RouteSegment.objects.filter(pattern_id__in=pattern_ids).values_list(
        "pattern_id", "from_occurrence_id", "to_occurrence_id", "distance_m",
        "riding_seconds", "estimate_basis", "source_id",
    ).iterator(chunk_size=5000):
        seg_by_pattern.setdefault(row[0], []).append(SegmentData(
            from_occurrence_id=str(row[1]), to_occurrence_id=str(row[2]),
            distance_m=row[3], riding_seconds=row[4], estimate_basis=row[5] or None,
            source_ids=((str(row[6]),) if row[6] else ()),
        ))

    # Evidence whose status is within the active gate (documented evidence
    # counts when documented data is enabled; rejected never counts).
    ev_by_pattern: dict = {}
    for pid, src_id in RouteEvidence.objects.filter(
        pattern_id__in=pattern_ids, status__in=statuses
    ).values_list("pattern_id", "source_id"):
        ev_by_pattern.setdefault(pid, set()).add(str(src_id))

    for pid, route_id, direction, variant_key, signboard, status, verified_at in pattern_rows:
        if str(route_id) not in net.routes or pid not in occ_by_pattern:
            continue
        net.patterns.append(PatternData(
            id=str(pid), route_id=str(route_id), direction=direction,
            variant_key=variant_key, signboard=signboard or None, status=status,
            verified_at=verified_at.isoformat() if verified_at else None,
            stops=tuple(occ_by_pattern[pid]),
            segments=tuple(seg_by_pattern.get(pid, ())),
            evidence_source_ids=tuple(sorted(ev_by_pattern.get(pid, ()))),
        ))

    for t in TransferConnection.objects.filter(status__in=statuses):
        net.transfers.append(TransferData(
            id=str(t.id), from_stop_id=str(t.from_stop_id), to_stop_id=str(t.to_stop_id),
            distance_m=t.distance_m, duration_seconds=t.duration_seconds,
            status=t.status, source_ids=((str(t.source_id),) if t.source_id else ()),
        ))

    for f in FareRule.objects.filter(status="verified").select_related("source"):
        net.fares.append(FarePolicy(
            id=str(f.id), vehicle_class=f.vehicle_class,
            route_id=str(f.route_id) if f.route_id else None,
            pattern_id=str(f.pattern_id) if f.pattern_id else None,
            passenger_category=f.passenger_category, currency=f.currency,
            kind=f.kind, policy=f.policy, valid_from=f.valid_from,
            valid_until=f.valid_until, status=f.status,
            source_ids=((str(f.source_id),) if f.source_id else ()),
        ))

    return net


def resolve_location(location_id: str) -> Optional[Location]:
    from django.core.exceptions import ValidationError

    try:
        return Location.objects.get(id=location_id)
    except (Location.DoesNotExist, ValidationError, ValueError, TypeError):
        return None
