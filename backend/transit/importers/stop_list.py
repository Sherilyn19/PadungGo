"""Turn a typed-in list of stops into a route direction.

Used where no outside map data exists for a route, for example the part of a
route that the imported feed cuts short, or routes on Mactan Island. A rider who
knows the route lists its stops in order. Nothing is guessed: a stop with no
coordinates is matched only to ONE known place of the same name, otherwise the
list is refused and the row is named.

Distances are straight lines between consecutive stops (real roads are longer),
and the route is stored as "documented", never "verified". The preview shows
every distance so a wrong coordinate is easy to spot before anything is saved.
"""
from __future__ import annotations

import csv
import io
import zlib

from transit.models import Location
from transit.planner.geo import haversine_m

from .osm_route import MappedRoute, MappedStop, OSMRouteError

MAX_CHARS = 200_000
MAX_ROWS = 2000
# One hop longer than this is almost always a typo in a coordinate.
MAX_HOP_M = 8000
COLUMNS = ("route_code", "direction", "stop_name", "latitude", "longitude")
EXAMPLE = (
    "route_code,direction,stop_name,latitude,longitude\n"
    "XX1,Town to Beach,Town Plaza,10.3000,123.9000\n"
    "XX1,Town to Beach,Public Market,10.3050,123.9050\n"
    "XX1,Town to Beach,Beach Terminal,\n"
)


def _number(value: str, low: float, high: float, row: int, label: str) -> float:
    try:
        number = float(value)
    except ValueError:
        raise OSMRouteError(f"Row {row}: {label} \u201c{value}\u201d is not a number.") from None
    if not low <= number <= high:
        raise OSMRouteError(f"Row {row}: {label} {number} is outside Metro Cebu.")
    return number


def _place_coordinates(name: str, row: int) -> tuple[float, float]:
    """Only an exact, single match is trusted; anything else must be typed in."""
    matches = list(Location.objects.filter(name__iexact=name).values_list("latitude", "longitude")[:3])
    if len(matches) != 1:
        why = "no known place has" if not matches else "more than one known place has"
        raise OSMRouteError(f"Row {row}: {why} the name \u201c{name}\u201d. Type its latitude and longitude instead.")
    return matches[0]


def parse_stop_list(text: str) -> list[MappedRoute]:
    """One MappedRoute per (route_code, direction) group of rows, in the order typed."""
    if len(text) > MAX_CHARS:
        raise OSMRouteError("That list is too long.")
    rows = list(csv.reader(io.StringIO(text.strip())))
    if not rows or tuple(c.strip().lower() for c in rows[0]) != COLUMNS:
        raise OSMRouteError("The first line must be exactly: " + ",".join(COLUMNS))
    if len(rows) - 1 > MAX_ROWS:
        raise OSMRouteError("That list has too many rows.")

    groups: dict[tuple[str, str], list[MappedStop]] = {}
    for number, cells in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in cells):
            continue
        cells = [c.strip() for c in cells] + [""] * (len(COLUMNS) - len(cells))
        code, direction, name, lat_text, lon_text = cells[:5]
        if not code or not name:
            raise OSMRouteError(f"Row {number}: route_code and stop_name are required.")
        if lat_text and lon_text:
            lat = _number(lat_text, 9.9, 11.3, number, "latitude")
            lon = _number(lon_text, 123.2, 124.4, number, "longitude")
        else:
            lat, lon = _place_coordinates(name, number)
        key = " ".join(name.casefold().split()), round(lat, 5), round(lon, 5)
        # Same name and place always gets the same id, so two directions share one stop.
        stop_id = zlib.crc32(repr(key).encode())
        groups.setdefault((code, direction), []).append(
            MappedStop(stop_id, " ".join(name.split())[:200], lat, lon, "platform"))

    routes = []
    for (code, direction), stops in groups.items():
        for a, b in zip(stops, stops[1:]):
            hop = haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
            if hop > MAX_HOP_M:
                raise OSMRouteError(f"{code} ({direction}): \u201c{a.name}\u201d to \u201c{b.name}\u201d is "
                                    f"{hop / 1000:.1f} km apart, which looks like a wrong coordinate.")
        path = [(s.latitude, s.longitude) for s in stops]
        label = direction or code
        key = zlib.crc32(f"{code}|{direction}".encode())
        routes.append(MappedRoute(
            relation_id=key, ref=code, name=label, stops=stops, path=path,
            variant_key=f"list:{code}:{key:08x}", source_kind="list"))
    return routes
