"""Project ordered GTFS stops onto sourced route shapes."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from transit.planner.geo import haversine_m


@dataclass
class ShapeProjection:
    index: int        # Shape segment index.
    t: float          # Fraction along that segment.
    along_m: float    # Cumulative metres along the shape.
    offset_m: float    # Distance from the stop to the shape.
    lat: float
    lon: float


def project_stops(
    shape: list[tuple[float, float]], stops: list[tuple[float, float]],
) -> Optional[list[ShapeProjection]]:
    """Project stops forward along a shape; return None for unusable shapes."""
    if len(shape) < 2:
        return None
    lat0 = shape[0][0]
    kx = 111_320.0 * math.cos(math.radians(lat0))
    ky = 110_540.0
    xy = [(lon * kx, lat * ky) for lat, lon in shape]
    cumulative = [0.0]
    for i in range(1, len(shape)):
        cumulative.append(cumulative[-1] + haversine_m(*shape[i - 1], *shape[i]))

    projections = []
    start = 0
    for lat, lon in stops:
        px, py = lon * kx, lat * ky
        candidates = []
        for i in range(start, len(xy) - 1):
            (x1, y1), (x2, y2) = xy[i], xy[i + 1]
            dx, dy = x2 - x1, y2 - y1
            squared_length = dx * dx + dy * dy
            t = (
                0.0 if squared_length == 0
                else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / squared_length))
            )
            qx, qy = x1 + t * dx, y1 + t * dy
            candidates.append((math.hypot(px - qx, py - qy), i, t))
        if not candidates:
            return None
        best = min(candidate[0] for candidate in candidates)
        # Prefer the earliest near-best segment to avoid jumping ahead on loops.
        offset, i, t = next(candidate for candidate in candidates if candidate[0] <= best + 30.0)
        segment_length = cumulative[i + 1] - cumulative[i]
        projected_lat = shape[i][0] + t * (shape[i + 1][0] - shape[i][0])
        projected_lon = shape[i][1] + t * (shape[i + 1][1] - shape[i][1])
        along = cumulative[i] + t * segment_length
        if projections and along < projections[-1].along_m:
            along = projections[-1].along_m
        projections.append(ShapeProjection(i, t, along, offset, projected_lat, projected_lon))
        start = i
    return projections


def slice_shape(
    shape: list[tuple[float, float]],
    start: ShapeProjection,
    end: ShapeProjection,
) -> list[tuple[float, float]]:
    points = [(start.lat, start.lon)]
    points.extend(shape[start.index + 1: end.index + 1])
    points.append((end.lat, end.lon))
    return points
