"""
ORM -> planner dataclass loader. The ONLY planner module that touches Django.

Builds an in-memory Network from database records without loading route geometry.
Supports both PostGIS and lite/SQLite modes.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from django.db.models import F

from transit.models import (
    DataSource,
    NetworkDataVersion,
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
from transit.planner.eligibility import allowed_statuses
from transit.planner.journey_types import (
    FarePolicy,
    Network,
    PatternData,
    PatternStopData,
    RouteData,
    SegmentData,
    StopData,
    TransferData,
)


@dataclass(frozen=True)
class _CachedNetwork:
    loaded_at: float  # time.monotonic() when loading started
    data_version: int  # NetworkDataVersion.version the copy was built from
    network: Network


# One copy per server process, keyed by "include documented data?".
_CACHE: dict[bool, _CachedNetwork] = {}
# Safety net for changes made outside Django (e.g. raw SQL), which do not bump
# the shared version.
_CACHE_TTL_S = 300.0


def _current_data_version() -> int:
    """Read the shared version (one primary-key lookup)."""
    row = NetworkDataVersion.objects.filter(pk=NetworkDataVersion.SINGLETON_ID).values_list(
        "version", flat=True
    ).first()
    return row or 0


def invalidate_network_cache() -> None:
    """Mark the planner network as changed for every server process.

    Clears this process's copy and bumps the shared version, so other workers
    and other processes reload on their next request. Called by the model
    signals (admin edits) and at the end of a GTFS import. When called inside a
    transaction, the bump becomes visible only when that transaction commits,
    which is exactly when the new data does.
    """
    _CACHE.clear()
    updated = NetworkDataVersion.objects.filter(pk=NetworkDataVersion.SINGLETON_ID).update(
        version=F("version") + 1
    )
    if not updated:
        NetworkDataVersion.objects.get_or_create(pk=NetworkDataVersion.SINGLETON_ID)


def load_network(*, allow_documented: bool = False, use_cache: bool = True) -> Network:
    """Load the routable network, cached in-process.

    Only public, non-personal route data is cached. A cached copy is reused
    only while the shared data version still matches and it is younger than the
    TTL, so imports and admin edits made by any process show up on the next
    request.
    """
    started = time.monotonic()
    # Read the version BEFORE loading: if data changes while we load, the stored
    # version is already out of date and the next request reloads.
    data_version = _current_data_version()
    hit = _CACHE.get(allow_documented)
    if (
        use_cache
        and hit is not None
        and hit.data_version == data_version
        and started - hit.loaded_at < _CACHE_TTL_S
    ):
        return hit.network
    network = _load_network(allow_documented)
    _CACHE[allow_documented] = _CachedNetwork(started, data_version, network)
    return network


def _load_network(allow_documented: bool) -> Network:
    network = Network()
    statuses = allowed_statuses(allow_documented)
    _load_sources(network)
    _load_stops(network)
    _load_routes(network)
    _load_patterns(network, statuses)
    _load_transfers(network, statuses)
    _load_fares(network)
    return network


def _load_sources(network: Network) -> None:
    for source in DataSource.objects.all():
        network.sources[str(source.id)] = {
            "id": str(source.id),
            "title": source.title,
            "publisher": source.publisher,
            "reference": source.reference,
            "published_at": source.published_at.isoformat() if source.published_at else None,
            "license": source.license,
        }


def _load_stops(network: Network) -> None:
    # Select scalar fields to avoid loading geometry for a city-sized network.
    for row in Stop.objects.values_list(
        "id", "name", "latitude", "longitude", "can_board", "can_alight", "status"
    ).iterator(chunk_size=2000):
        stop_id = str(row[0])
        network.stops[stop_id] = StopData(
            id=stop_id, name=row[1], latitude=row[2], longitude=row[3],
            can_board=row[4], can_alight=row[5], status=row[6],
        )


def _load_routes(network: Network) -> None:
    for row in Route.objects.filter(active=True).values_list(
        "id", "code", "name", "vehicle_class", "operator"
    ):
        route_id = str(row[0])
        network.routes[route_id] = RouteData(
            id=route_id, code=row[1], name=row[2], vehicle_class=row[3], operator=row[4] or None,
        )


def _load_pattern_stops(pattern_ids: list) -> dict:
    stops_by_pattern: dict = {}
    for row in PatternStop.objects.filter(pattern_id__in=pattern_ids).values_list(
        "pattern_id", "id", "stop_id", "sequence", "distance_along_m", "can_board", "can_alight"
    ).order_by("pattern_id", "sequence").iterator(chunk_size=5000):
        stops_by_pattern.setdefault(row[0], []).append(PatternStopData(
            id=str(row[1]), stop_id=str(row[2]), sequence=row[3],
            distance_along_m=row[4], can_board=row[5], can_alight=row[6],
        ))
    return stops_by_pattern


def _load_pattern_segments(pattern_ids: list) -> dict:
    segments_by_pattern: dict = {}
    for row in RouteSegment.objects.filter(pattern_id__in=pattern_ids).values_list(
        "pattern_id", "from_occurrence_id", "to_occurrence_id", "distance_m",
        "riding_seconds", "estimate_basis", "source_id",
    ).iterator(chunk_size=5000):
        segments_by_pattern.setdefault(row[0], []).append(SegmentData(
            from_occurrence_id=str(row[1]), to_occurrence_id=str(row[2]),
            distance_m=row[3], riding_seconds=row[4], estimate_basis=row[5] or None,
            source_ids=((str(row[6]),) if row[6] else ()),
        ))
    return segments_by_pattern


def _load_pattern_evidence(pattern_ids: list, statuses: frozenset[str]) -> dict:
    # Documented evidence counts only when documented data is enabled.
    evidence_by_pattern: dict = {}
    for pattern_id, source_id in RouteEvidence.objects.filter(
        pattern_id__in=pattern_ids, status__in=statuses
    ).values_list("pattern_id", "source_id"):
        evidence_by_pattern.setdefault(pattern_id, set()).add(str(source_id))
    return evidence_by_pattern


def _load_patterns(network: Network, statuses: frozenset[str]) -> None:
    pattern_rows = list(
        RoutePattern.objects.filter(status__in=statuses, route__active=True).values_list(
            "id", "route_id", "direction", "variant_key", "signboard", "status", "verified_at"
        )
    )
    pattern_ids = [row[0] for row in pattern_rows]
    stops_by_pattern = _load_pattern_stops(pattern_ids)
    segments_by_pattern = _load_pattern_segments(pattern_ids)
    evidence_by_pattern = _load_pattern_evidence(pattern_ids, statuses)

    for pattern_id, route_id, direction, variant_key, signboard, status, verified_at in pattern_rows:
        if str(route_id) not in network.routes or pattern_id not in stops_by_pattern:
            continue
        network.patterns.append(PatternData(
            id=str(pattern_id), route_id=str(route_id), direction=direction,
            variant_key=variant_key, signboard=signboard or None, status=status,
            verified_at=verified_at.isoformat() if verified_at else None,
            stops=tuple(stops_by_pattern[pattern_id]),
            segments=tuple(segments_by_pattern.get(pattern_id, ())),
            evidence_source_ids=tuple(sorted(evidence_by_pattern.get(pattern_id, ()))),
        ))


def _load_transfers(network: Network, statuses: frozenset[str]) -> None:
    for transfer in TransferConnection.objects.filter(status__in=statuses):
        network.transfers.append(TransferData(
            id=str(transfer.id),
            from_stop_id=str(transfer.from_stop_id),
            to_stop_id=str(transfer.to_stop_id),
            distance_m=transfer.distance_m,
            duration_seconds=transfer.duration_seconds,
            status=transfer.status,
            source_ids=((str(transfer.source_id),) if transfer.source_id else ()),
        ))


def _load_fares(network: Network) -> None:
    # Fare rules remain verified-only even when documented routes are enabled.
    for fare in FareRule.objects.filter(status="verified").select_related("source"):
        network.fares.append(FarePolicy(
            id=str(fare.id), vehicle_class=fare.vehicle_class,
            route_id=str(fare.route_id) if fare.route_id else None,
            pattern_id=str(fare.pattern_id) if fare.pattern_id else None,
            passenger_category=fare.passenger_category, currency=fare.currency,
            kind=fare.kind, policy=fare.policy, valid_from=fare.valid_from,
            valid_until=fare.valid_until, status=fare.status,
            source_ids=((str(fare.source_id),) if fare.source_id else ()),
        ))


def resolve_location(location_id: str) -> Optional[Location]:
    from django.core.exceptions import ValidationError

    try:
        return Location.objects.get(id=location_id)
    except (Location.DoesNotExist, ValidationError, ValueError, TypeError):
        return None
