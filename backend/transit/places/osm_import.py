"""Import named places in Cebu City, Mandaue and Lapu-Lapu from OpenStreetMap.

Schools, hospitals, malls, landmarks, attractions, offices and terminals become
searchable Location records, so typing a name, a word or an acronym ("usjr",
"cnu") finds them. They only describe where a place is; they are never
evidence about routes. OpenStreetMap data is ODbL-licensed and must be credited.

Re-running updates records by their OpenStreetMap id (Location.external_ref);
hand-made locations and GTFS stop locations are never touched.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from django.db import transaction
from django.utils import timezone

from transit.geocompat import make_point
from transit.models import Area, DataSource, Location
from transit.models.enums import AreaKind, RecordStatus
from transit.planner.geo import haversine_m
from transit.search_text import build_search_text

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "PadungGo/1.0 (+https://github.com/Sherilyn19/PadungGo)"
SOURCE_TITLE = "OpenStreetMap places (Cebu City, Mandaue, Lapu-Lapu)"
SOURCE_REFERENCE = "https://www.openstreetmap.org/copyright"
TIMEOUT_SECONDS = 180
# OpenStreetMap spells the cities "Cebu City", "Mandaue", "Lapu-Lapu".
CITY_NAMES = ("Cebu City", "Mandaue", "Lapu-Lapu")
# Same name this close together is one place mapped twice (e.g. node + building).
DUPLICATE_DISTANCE_M = 80

# OpenStreetMap tag -> values worth searching for, and the Location kind they map to.
_WANTED = {
    "amenity": {
        "university": "school", "college": "school", "school": "school",
        "hospital": "landmark", "clinic": "landmark", "townhall": "landmark",
        "police": "landmark", "fire_station": "landmark", "courthouse": "landmark",
        "library": "landmark", "place_of_worship": "landmark", "marketplace": "landmark",
        "bus_station": "terminal", "ferry_terminal": "terminal", "cinema": "business",
        "bank": "business",
    },
    "shop": {"mall": "mall", "department_store": "mall", "supermarket": "business"},
    "tourism": {"attraction": "attraction", "museum": "attraction", "viewpoint": "attraction",
                "hotel": "business", "theme_park": "attraction", "zoo": "attraction"},
    "historic": {"monument": "attraction", "memorial": "attraction", "fort": "attraction",
                 "church": "attraction", "building": "attraction", "castle": "attraction"},
    "leisure": {"park": "landmark", "stadium": "landmark", "sports_centre": "landmark"},
    "office": {"government": "business", "company": "business"},
    "aeroway": {"aerodrome": "transport_hub", "terminal": "transport_hub"},
    "public_transport": {"station": "terminal"},
}


def overpass_query() -> str:
    names = "|".join(CITY_NAMES)
    selectors = "".join(
        f'nwr(area.c)["name"]["{key}"~"^({"|".join(values)})$"];'
        for key, values in _WANTED.items()
    )
    # One query: for each city boundary, its tags first, then its places.
    return (
        f'[out:json][timeout:{TIMEOUT_SECONDS}];'
        f'rel["boundary"="administrative"]["admin_level"="6"]["name"~"^({names})$"];'
        f'map_to_area->.cities;'
        f'foreach.cities->.c(.c out tags;({selectors});out center tags;);'
    )


class OSMImportError(Exception):
    pass


def fetch_overpass(query: str) -> dict:
    body = urllib.parse.urlencode({"data": query}).encode()
    request = urllib.request.Request(OVERPASS_URL, data=body, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS + 30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise OSMImportError(
            "OpenStreetMap's server did not answer. It is shared and sometimes busy; "
            "try again in a few minutes.") from exc


@dataclass
class PlaceRow:
    ref: str
    name: str
    aliases: str
    kind: str
    city: str
    latitude: float
    longitude: float


def _kind(tags: dict) -> str | None:
    for key, values in _WANTED.items():
        kind = values.get(tags.get(key, ""))
        if kind:
            return kind
    return None


def _aliases(tags: dict, name: str) -> str:
    """Other names mappers recorded, e.g. short_name "USC" or old_name."""
    found = []
    for key in ("short_name", "alt_name", "official_name", "old_name", "name:en"):
        for value in (tags.get(key) or "").split(";"):
            value = value.strip()
            if value and value != name and value not in found:
                found.append(value)
    return ", ".join(found)[:500]


def parse_places(data: dict) -> list[PlaceRow]:
    rows: list[PlaceRow] = []
    city = None
    for element in data.get("elements", []):
        tags = element.get("tags") or {}
        if tags.get("boundary") == "administrative":
            city = tags.get("name")
            continue
        name = " ".join((tags.get("name") or "").split())
        kind = _kind(tags)
        point = element.get("center") or element
        lat, lon = point.get("lat"), point.get("lon")
        if not (city and name and kind and isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            continue
        row = PlaceRow(ref=f"osm:{element['type']}/{element['id']}", name=name[:200],
                       aliases=_aliases(tags, name), kind=kind, city=city,
                       latitude=float(lat), longitude=float(lon))
        if not any(r.name == row.name and haversine_m(r.latitude, r.longitude, lat, lon)
                   <= DUPLICATE_DISTANCE_M for r in rows):
            rows.append(row)
    return rows


@dataclass
class OSMImportReport:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    by_city: dict = field(default_factory=dict)


def _city_area(name: str) -> Area:
    found = Area.objects.filter(name=name, kind=AreaKind.CITY).order_by("id").first()
    return found or Area.objects.create(name=name, kind=AreaKind.CITY)


def save_places(rows: list[PlaceRow]) -> OSMImportReport:
    """Create or update imported places in bulk (a few queries, not one per place)."""
    report = OSMImportReport()
    fields = ["name", "aliases", "kind", "area", "latitude", "longitude", "point", "search_text"]
    with transaction.atomic():
        source, _ = DataSource.objects.get_or_create(
            title=SOURCE_TITLE, reference=SOURCE_REFERENCE,
            defaults={"publisher": "OpenStreetMap contributors",
                      "license": "ODbL 1.0 (© OpenStreetMap contributors)",
                      "collected_at": timezone.now(),
                      "limitations": "Place locations only; not evidence of routes or stops."})
        source.collected_at = timezone.now()
        source.save(update_fields=["collected_at"])
        areas = {name: _city_area(name) for name in {r.city for r in rows}}
        existing = {loc.external_ref: loc for loc in
                    Location.objects.filter(external_ref__startswith="osm:")}
        new, changed = [], []
        for row in rows:
            report.by_city[row.city] = report.by_city.get(row.city, 0) + 1
            values = {"name": row.name, "aliases": row.aliases, "kind": row.kind,
                      "area": areas[row.city], "latitude": row.latitude,
                      "longitude": row.longitude,
                      # bulk operations skip save(), so fill the search words here.
                      "search_text": build_search_text(row.name, row.aliases)}
            location = existing.get(row.ref)
            if location is None:
                new.append(Location(external_ref=row.ref, source=source,
                                    status=RecordStatus.DOCUMENTED,
                                    point=make_point(row.latitude, row.longitude), **values))
            elif all(getattr(location, k) == v for k, v in values.items()):
                report.unchanged += 1
            else:
                for k, v in values.items():
                    setattr(location, k, v)
                location.point = make_point(row.latitude, row.longitude)
                changed.append(location)
        Location.objects.bulk_create(new, batch_size=500)
        Location.objects.bulk_update(changed, fields, batch_size=500)
        report.created, report.updated = len(new), len(changed)
    return report


def import_osm_places() -> OSMImportReport:
    rows = parse_places(fetch_overpass(overpass_query()))
    if not rows:
        raise OSMImportError("OpenStreetMap returned no places; nothing was changed.")
    return save_places(rows)

