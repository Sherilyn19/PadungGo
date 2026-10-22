"""Pure-Python dataclasses the planner operates on (no Django imports)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


# --- Request / endpoints ---------------------------------------------------


@dataclass(frozen=True)
class Endpoint:
    """A resolved request endpoint. Either a location_id or raw coordinates."""

    latitude: float
    longitude: float
    location_id: Optional[str] = None
    name: Optional[str] = None


@dataclass(frozen=True)
class PlanRequest:
    origin: Endpoint
    destination: Endpoint
    max_transfers: int = 1
    limit: int = 5
    sort_by: str = "fewest_transfers"
    query_date: Optional[date] = None  # for fare validity; None => today at call site


# --- Network records -------------------------------------------------------


@dataclass(frozen=True)
class StopData:
    id: str
    name: str
    latitude: float
    longitude: float
    can_board: bool = True
    can_alight: bool = True
    status: str = "candidate"


@dataclass(frozen=True)
class PatternStopData:
    id: str
    stop_id: str
    sequence: int
    distance_along_m: int
    can_board: bool
    can_alight: bool


@dataclass(frozen=True)
class SegmentData:
    from_occurrence_id: str
    to_occurrence_id: str
    distance_m: int
    riding_seconds: Optional[int]
    estimate_basis: Optional[str]
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteData:
    id: str
    code: str
    name: str
    vehicle_class: str
    operator: Optional[str]
    service_availability: str = "not_flagged"


@dataclass(frozen=True)
class PatternData:
    id: str
    route_id: str
    direction: str
    variant_key: str
    signboard: Optional[str]
    status: str
    verified_at: Optional[str]
    stops: tuple[PatternStopData, ...]
    segments: tuple[SegmentData, ...]
    evidence_source_ids: tuple[str, ...] = ()
    has_verified_evidence: bool = False

    def occurrence_by_id(self, occ_id: str) -> Optional[PatternStopData]:
        for s in self.stops:
            if s.id == occ_id:
                return s
        return None


@dataclass(frozen=True)
class TransferData:
    id: str
    from_stop_id: str
    to_stop_id: str
    distance_m: int
    duration_seconds: Optional[int]
    status: str
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FarePolicy:
    id: str
    vehicle_class: str
    route_id: Optional[str]
    pattern_id: Optional[str]
    passenger_category: str
    currency: str
    kind: str
    policy: dict
    valid_from: date
    valid_until: Optional[date]
    status: str
    source_ids: tuple[str, ...] = ()

    @property
    def specificity(self) -> int:
        if self.pattern_id:
            return 2
        if self.route_id:
            return 1
        return 0


@dataclass
class Network:
    """In-memory view of the routable network the planner searches over."""

    routes: dict[str, RouteData] = field(default_factory=dict)
    patterns: list[PatternData] = field(default_factory=list)
    stops: dict[str, StopData] = field(default_factory=dict)
    transfers: list[TransferData] = field(default_factory=list)
    fares: list[FarePolicy] = field(default_factory=list)
    # DataSource id -> public reference metadata for evidence output.
    sources: dict[str, dict] = field(default_factory=dict)


# --- Result ----------------------------------------------------------------


@dataclass
class PlanResult:
    request_coverage_status: str
    reason: Optional[str]
    journey_options: list[dict]
    ranking: dict
    warnings: list[str]

    def to_dict(self) -> dict:
        return {
            "request_coverage_status": self.request_coverage_status,
            "reason": self.reason,
            "journey_options": self.journey_options,
            "ranking": self.ranking,
            "warnings": self.warnings,
        }
