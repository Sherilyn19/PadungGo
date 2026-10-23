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
import logging
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from django.db import DatabaseError, transaction
from django.utils import timezone

from transit.geocompat import make_point
from transit.models import Area, DataSource, Location
from transit.models.enums import AreaKind, RecordStatus
from transit.planner.geo import haversine_m
from transit.search_text import build_search_text

logger = logging.getLogger(__name__)

# Settable in Render if the public server ever needs to be swapped (no code change).
OVERPASS_URL = os.environ.get("OVERPASS_URL", "https://overpass-api.de/api/interpreter")
USER_AGENT = "PadungGo/1.0 (+https://github.com/Sherilyn19/PadungGo)"
SOURCE_TITLE = "OpenStreetMap places (Cebu City, Mandaue, Lapu-Lapu)"
SOURCE_REFERENCE = "https://www.openstreetmap.org/copyright"
# Overpass gives up on a query after this long; our wait is a little longer.
QUERY_TIMEOUT_SECONDS = 90
ATTEMPT_TIMEOUT_SECONDS = 100
MAX_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (5, 15)
# The whole download must end before Gunicorn's 300 s worker limit, leaving time to save.
TOTAL_BUDGET_SECONDS = 240
MIN_ATTEMPT_SECONDS = 30
MAX_REPLY_BYTES = 30 * 1024 * 1024
RETRYABLE_STATUSES = frozenset({429, 502, 503, 504})
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


def overpass_query(city: str | None = None) -> str:
    """Query for one city, or all three when `city` is None."""
    if city is not None and city not in CITY_NAMES:
        raise ValueError(f"Unknown city: {city}")
    names = city if city else "|".join(CITY_NAMES)
    selectors = "".join(
        f'nwr(area.c)["name"]["{key}"~"^({"|".join(values)})$"];'
        for key, values in _WANTED.items()
    )
    # For each city boundary: its tags first, then its places.
    return (
        f'[out:json][timeout:{QUERY_TIMEOUT_SECONDS}];'
        f'rel["boundary"="administrative"]["admin_level"="6"]["name"~"^({names})$"];'
        f'map_to_area->.cities;'
        f'foreach.cities->.c(.c out tags;({selectors});out center tags;);'
    )


def download_url(city: str) -> str:
    """A link that downloads one city's data in a browser (for the file fallback)."""
    return f"{OVERPASS_URL}?data={urllib.parse.quote(overpass_query(city))}"


class OSMImportError(Exception):
    """The message says what really failed and is safe to show to Admin staff."""


class _AttemptFailed(Exception):
    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.message = message
        self.retryable = retryable


def _http_message(code: int) -> str:
    if code == 429:
        return "the server is limiting how often it can be asked (HTTP 429)"
    if code in (502, 503, 504):
        return f"the server is overloaded or restarting (HTTP {code})"
    if code in (403, 406):
        return f"the server refused this app's request (HTTP {code}); the app may be blocked"
    return f"the server answered with an error (HTTP {code})"


def _parse_reply(raw: bytes) -> dict:
    """Turn a reply into Overpass data, rejecting pages, errors and partial results."""
    try:
        data = json.loads(raw)
    except ValueError:
        raise _AttemptFailed("the server sent a web page instead of data (it is usually busy)", True) from None
    if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
        raise _AttemptFailed("the reply was not Overpass place data", False)
    remark = str(data.get("remark") or "")
    # A "remark" means the query was cut short, so the places may be incomplete.
    if any(word in remark.lower() for word in ("runtime error", "timed out", "out of memory")):
        raise _AttemptFailed(f"the server stopped the query early ({remark[:140]})", True)
    return data


def _download_once(body: bytes, timeout: float) -> dict:
    request = urllib.request.Request(OVERPASS_URL, data=body, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_REPLY_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise _AttemptFailed(_http_message(exc.code), exc.code in RETRYABLE_STATUSES) from None
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise _AttemptFailed(f"no answer within {int(timeout)} seconds", True) from None
        raise _AttemptFailed(f"could not connect ({str(exc.reason)[:80]})", True) from None
    except (TimeoutError, socket.timeout):
        raise _AttemptFailed(f"no answer within {int(timeout)} seconds", True) from None
    except OSError as exc:
        raise _AttemptFailed(f"the connection broke ({type(exc).__name__})", True) from None
    if len(raw) > MAX_REPLY_BYTES:
        raise _AttemptFailed("the reply was unexpectedly large", False)
    return _parse_reply(raw)


def fetch_overpass(query: str) -> dict:
    """Download with a few retries, inside a time budget that fits one web request."""
    body = urllib.parse.urlencode({"data": query}).encode()
    deadline = time.monotonic() + TOTAL_BUDGET_SECONDS
    problems: list[str] = []
    for attempt in range(1, MAX_ATTEMPTS + 1):
        remaining = deadline - time.monotonic()
        if remaining < MIN_ATTEMPT_SECONDS:
            break
        try:
            return _download_once(body, min(ATTEMPT_TIMEOUT_SECONDS, remaining))
        except _AttemptFailed as exc:
            logger.warning("OpenStreetMap download attempt %s failed: %s", attempt, exc.message)
            problems.append(exc.message)
            if not exc.retryable or attempt == MAX_ATTEMPTS:
                break
            time.sleep(RETRY_DELAYS_SECONDS[attempt - 1])
    tries = len(problems)
    last = problems[-1] if problems else "there was not enough time left to try"
    raise OSMImportError(
        f"Could not download from OpenStreetMap after {tries} {'try' if tries == 1 else 'tries'}. "
        f"Last problem: {last}. Nothing was changed. Try again in a few minutes, "
        "or use the file option below."
    )


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
    download_seconds: float | None = None
    save_seconds: float = 0.0


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


def _save_checked(data: dict) -> OSMImportReport:
    rows = parse_places(data)
    if not rows:
        raise OSMImportError("No matching places were found in that data; nothing was changed.")
    started = time.monotonic()
    try:
        report = save_places(rows)
    except DatabaseError:
        logger.exception("Saving OpenStreetMap places failed")
        raise OSMImportError(
            "The places were downloaded, but saving them to the database failed. "
            "Nothing was changed (it is all-or-nothing). Details are in the Render logs."
        ) from None
    report.save_seconds = time.monotonic() - started
    return report


def import_osm_places(city: str | None = None) -> OSMImportReport:
    """Download one city (or all three) from OpenStreetMap and save the places."""
    started = time.monotonic()
    data = fetch_overpass(overpass_query(city))
    downloaded = time.monotonic() - started
    report = _save_checked(data)
    report.download_seconds = downloaded
    return report


def import_osm_file(raw: bytes) -> OSMImportReport:
    """Save places from a file of Overpass data downloaded in a browser."""
    if len(raw) > MAX_REPLY_BYTES:
        raise OSMImportError("That file is too large to be one city's data.")
    try:
        data = _parse_reply(raw)
    except _AttemptFailed as exc:
        raise OSMImportError(f"This file cannot be used: {exc.message}.") from None
    return _save_checked(data)
