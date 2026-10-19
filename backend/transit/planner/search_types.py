"""Pure-Python records shared by journey search and assembly."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .journey_types import Network, PatternData, PatternStopData, TransferData


@dataclass(frozen=True)
class StopCandidate:
    stop_id: str
    straight_line_m: float


OccurrenceIndex = dict[str, list[tuple[PatternData, PatternStopData]]]


@dataclass(frozen=True)
class SearchContext:
    network: Network
    origin_stops: list[StopCandidate]
    destination_stops: list[StopCandidate]
    destination_ids: set[str]
    straight_line_by_stop: dict[str, float]
    occurrences_by_stop: OccurrenceIndex
    allowed_statuses: frozenset[str]
    passenger_category: str
    on: date


@dataclass(frozen=True)
class RideLeg:
    pattern: PatternData
    board: PatternStopData
    alight: PatternStopData


@dataclass(frozen=True)
class TransferCandidate:
    first_leg: RideLeg
    connection: TransferData
    second_leg: RideLeg
    ride_distance_m: int