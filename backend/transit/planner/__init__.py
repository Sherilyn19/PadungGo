"""
PadungGo deterministic journey planner.

Pure Python. This package MUST NOT import Django or django.contrib.gis so its
tests run without a database or GDAL/GEOS. The ORM->dataclass loader lives in
`transit.planner.loader` and is the only place that touches models.

Design source of truth: docs/ROUTING_ALGORITHM.md and docs/API_DESIGN.md.

Guiding rule: never fabricate routes, stops, transfers, fares, waits or ETAs.
Unknown is represented as None and is never treated as zero.
"""
from .engine import plan_journeys
from .models import (
    FarePolicy,
    Network,
    PatternData,
    PatternStopData,
    PlanRequest,
    PlanResult,
    RouteData,
    SegmentData,
    StopData,
    TransferData,
)

__all__ = [
    "plan_journeys",
    "PlanRequest",
    "PlanResult",
    "Network",
    "RouteData",
    "PatternData",
    "PatternStopData",
    "SegmentData",
    "StopData",
    "TransferData",
    "FarePolicy",
]
