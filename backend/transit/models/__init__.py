"""
PadungGo domain models.

Canonical schema per docs/DATABASE_DESIGN.md. Direction-aware route patterns,
stop occurrences, versioned source-backed fares, and append-only evidence.

Units everywhere: distance in metres (integer), duration in seconds (integer),
money in integer centavos. Unknown values are NULL and must never be read as 0.
"""
from .enums import (
    AreaKind,
    EstimateBasis,
    EvidenceStatus,
    FarePolicyKind,
    LocationKind,
    PassengerCategory,
    PatternDirection,
    RecordStatus,
    StopStatus,
    VehicleClass,
)
from .cache import NetworkDataVersion
from .evidence import DataSource, RecordEvidence, RouteEvidence
from .fares import FareRule
from .geography import Area, Location, Stop
from .network import PatternStop, Route, RoutePattern, RouteSegment, TransferConnection
from .providers import ProviderUsage

__all__ = [
    # enums
    "AreaKind",
    "EstimateBasis",
    "EvidenceStatus",
    "FarePolicyKind",
    "LocationKind",
    "PassengerCategory",
    "PatternDirection",
    "RecordStatus",
    "StopStatus",
    "VehicleClass",
    # geography
    "Area",
    "Location",
    "Stop",
    # network
    "Route",
    "RoutePattern",
    "PatternStop",
    "RouteSegment",
    "TransferConnection",
    # fares
    "FareRule",
    # cache coordination
    "NetworkDataVersion",
    # external provider quota
    "ProviderUsage",
    # evidence
    "DataSource",
    "RouteEvidence",
    "RecordEvidence",
]
