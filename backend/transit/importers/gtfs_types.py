"""GTFS import options, reports, and parsed feed records."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


class GTFSImportError(Exception):
    pass


@dataclass
class ImportOptions:
    source_title: str
    source_reference: str = ""
    source_publisher: str = ""
    source_license: str = ""
    source_published_at: Optional[date] = None
    source_limitations: str = ""
    default_vehicle_class: str = "jeepney"
    same_stop_transfers: bool = True
    create_locations: bool = True


@dataclass
class ImportReport:
    routes: int = 0
    patterns: int = 0
    stops: int = 0
    locations: int = 0
    transfers: int = 0
    skipped_no_shape: int = 0
    skipped_off_shape: int = 0
    skipped_too_short: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"Imported {self.routes} routes, {self.patterns} patterns, {self.stops} stops, "
            f"{self.transfers} transfers, {self.locations} locations (all 'documented'). "
            f"Skipped patterns: {self.skipped_no_shape} without a shape, "
            f"{self.skipped_off_shape} with stops off their shape, "
            f"{self.skipped_too_short} with fewer than 2 stops."
        )


@dataclass
class FeedData:
    agencies: dict[str, str]
    routes: dict[str, dict]
    stops: dict[str, dict]
    patterns: dict[tuple, dict]
    shapes: dict[str, list[tuple[float, float]]]
    transfer_rows: list[dict]