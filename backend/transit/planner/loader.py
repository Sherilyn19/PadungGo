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


def load_network(*, allow_documented: bool = False) -> Network:
    """Load the routable network. For the MVP dataset size this loads all
    verified (optionally documented) records; bound by status to stay small."""
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

    for stop in Stop.objects.all():
        net.stops[str(stop.id)] = StopData(
            id=str(stop.id), name=stop.name,
            latitude=stop.latitude, longitude=stop.longitude,
            can_board=stop.can_board, can_alight=stop.can_alight,
            status=stop.status,
        )

    for route in Route.objects.filter(active=True):
        net.routes[str(route.id)] = RouteData(
            id=str(route.id), code=route.code, name=route.name,
            vehicle_class=route.vehicle_class, operator=route.operator or None,
        )

    patterns = (
        RoutePattern.objects
        .filter(status__in=statuses, route__active=True)
        .prefetch_related("pattern_stops", "segments", "evidence__source")
    )
    for pat in patterns:
        if str(pat.route_id) not in net.routes:
            continue
        occ = tuple(
            PatternStopData(
                id=str(ps.id), stop_id=str(ps.stop_id), sequence=ps.sequence,
                distance_along_m=ps.distance_along_m,
                can_board=ps.can_board, can_alight=ps.can_alight,
            )
            for ps in sorted(pat.pattern_stops.all(), key=lambda x: x.sequence)
        )
        segs = tuple(
            SegmentData(
                from_occurrence_id=str(sg.from_occurrence_id),
                to_occurrence_id=str(sg.to_occurrence_id),
                distance_m=sg.distance_m, riding_seconds=sg.riding_seconds,
                estimate_basis=sg.estimate_basis or None,
                source_ids=((str(sg.source_id),) if sg.source_id else ()),
            )
            for sg in pat.segments.all()
        )
        ev_sources = tuple(
            str(e.source_id) for e in pat.evidence.all()
            if e.status == "verified" and e.source_id
        )
        net.patterns.append(PatternData(
            id=str(pat.id), route_id=str(pat.route_id), direction=pat.direction,
            variant_key=pat.variant_key, signboard=pat.signboard or None,
            status=pat.status, verified_at=pat.verified_at.isoformat() if pat.verified_at else None,
            stops=occ, segments=segs, evidence_source_ids=ev_sources,
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
