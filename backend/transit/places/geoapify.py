"""Server-side Geoapify client for address labels and place suggestions.

Privacy: only the coordinates or the typed text are sent, from our server, so
Geoapify sees PadungGo's server rather than the user's device. Nothing here
logs coordinates, queries or request URLs (the URL contains the API key).

Quota: every request reserves one unit in a shared daily counter first, so
the app stays below the free plan's daily credits; results are cached.
"""
from __future__ import annotations

import hashlib
import json
import logging
import socket
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.utils import timezone

from transit.models import ProviderUsage
from transit.planner.geo import haversine_m
from transit.search_text import search_tokens

logger = logging.getLogger(__name__)

PROVIDER = "geoapify"
USER_AGENT = "PadungGo/1.0 (+https://padung-go.vercel.app)"
OSM_ATTRIBUTION = {"text": "© OpenStreetMap contributors",
                   "url": "https://www.openstreetmap.org/copyright"}
# Geoapify requires its own credit on the free plan, next to the data credit.
PROVIDER_ATTRIBUTION = {"text": "Powered by Geoapify", "url": "https://www.geoapify.com/"}

REVERSE_CACHE_SECONDS = 60 * 60
SUGGEST_CACHE_SECONDS = 24 * 60 * 60
RATE_LIMIT_PAUSE_SECONDS = 60
REJECTED_KEY_PAUSE_SECONDS = 10 * 60
CEBU_CITY_LON_LAT = "123.8854,10.3157"
SUGGESTION_LIMIT = 5


@dataclass
class ProviderResult:
    # ok | disabled | quota | rate_limited | timeout | error
    status: str
    results: list = field(default_factory=list)


def _config() -> dict:
    return settings.GEOAPIFY


def _reserve_request(share: float) -> bool:
    """Count one request against today's (UTC) limit; False when it is used up."""
    limit = int(_config()["DAILY_REQUEST_LIMIT"] * share)
    if limit <= 0:
        return False
    today = timezone.now().date()
    ProviderUsage.objects.get_or_create(provider=PROVIDER, day=today)
    # A single conditional UPDATE, so two workers cannot both take the last unit.
    updated = (ProviderUsage.objects
               .filter(provider=PROVIDER, day=today, requests__lt=limit)
               .update(requests=F("requests") + 1))
    return updated == 1


def _pause(status: str, seconds: int) -> None:
    cache.set(f"{PROVIDER}:paused", status, seconds)


def _fetch(path: str, params: dict, share: float) -> ProviderResult:
    config = _config()
    if not config["API_KEY"]:
        return ProviderResult("disabled")
    paused = cache.get(f"{PROVIDER}:paused")
    if paused:
        return ProviderResult(paused)
    if not _reserve_request(share):
        return ProviderResult("quota")

    query = urllib.parse.urlencode({**params, "format": "json", "lang": "en",
                                    "apiKey": config["API_KEY"]})
    request = urllib.request.Request(f"{config['BASE_URL']}/{path}?{query}",
                                     headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=config["TIMEOUT_SECONDS"]) as response:
            body = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            _pause("rate_limited", RATE_LIMIT_PAUSE_SECONDS)
            return ProviderResult("rate_limited")
        if exc.code in (401, 403):
            logger.warning("Geoapify rejected the API key (HTTP %s).", exc.code)
            _pause("error", REJECTED_KEY_PAUSE_SECONDS)
        return ProviderResult("error")
    except (TimeoutError, socket.timeout):
        return ProviderResult("timeout")
    except urllib.error.URLError as exc:
        timed_out = isinstance(exc.reason, (TimeoutError, socket.timeout))
        return ProviderResult("timeout" if timed_out else "error")
    except (ValueError, OSError):
        return ProviderResult("error")
    results = body.get("results") if isinstance(body, dict) else None
    return ProviderResult("ok", results if isinstance(results, list) else [])


def _data_attribution(result: dict) -> dict:
    """Credit the dataset Geoapify reports for this result (usually OpenStreetMap)."""
    source = result.get("datasource") or {}
    text = source.get("attribution")
    if isinstance(text, str) and text.strip():
        url = source.get("url") if isinstance(source.get("url"), str) else None
        return {"text": text.strip(), "url": url}
    return OSM_ATTRIBUTION


def _coordinate(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def reverse_address(latitude: float, longitude: float) -> dict:
    """Readable address for a point, or an honest reason why there is none.

    The returned latitude/longitude are always the caller's own values: a
    label never moves the point used for planning.
    """
    key = f"{PROVIDER}:rev:{latitude:.4f}:{longitude:.4f}"
    cached = cache.get(key)
    if cached is None:
        outcome = _fetch("reverse", {"lat": f"{latitude:.6f}", "lon": f"{longitude:.6f}",
                                     "limit": 1}, share=1.0)
        if outcome.status != "ok":
            return _address_payload("unavailable", latitude, longitude, reason=outcome.status)
        cached = _address_from(outcome.results, latitude, longitude)
        cache.set(key, cached, REVERSE_CACHE_SECONDS)
    return _address_payload(latitude=latitude, longitude=longitude, **cached)


def _address_from(results: list, latitude: float, longitude: float) -> dict:
    first = next((r for r in results if isinstance(r, dict)), None)
    label = first.get("formatted") if first else None
    if not isinstance(label, str) or not label.strip():
        return {"status": "no_result"}
    lat, lon = _coordinate(first.get("lat")), _coordinate(first.get("lon"))
    distance = _coordinate(first.get("distance"))
    if distance is None and lat is not None and lon is not None:
        distance = haversine_m(latitude, longitude, lat, lon)
    # A far-away match would describe a different place, so it is not shown.
    if distance is None or distance > _config()["MAX_ADDRESS_DISTANCE_M"]:
        return {"status": "no_result"}
    return {"status": "resolved", "label": label.strip(), "distance_m": round(distance),
            "attribution": [PROVIDER_ATTRIBUTION, _data_attribution(first)]}


def _address_payload(status: str, latitude: float, longitude: float, *, label=None,
                     distance_m=None, attribution=None, reason=None) -> dict:
    return {"status": status, "label": label, "latitude": latitude, "longitude": longitude,
            "distance_m": distance_m, "reason": reason, "attribution": attribution}


_KIND_PREFIXES = (
    ("education", "school"),
    ("tourism", "attraction"), ("entertainment", "attraction"), ("heritage", "attraction"),
    ("commercial", "business"), ("catering", "business"), ("office", "business"),
    ("accommodation", "business"), ("service", "business"),
)


def _kind(result: dict) -> str:
    category = result.get("category")
    if isinstance(category, str):
        for prefix, kind in _KIND_PREFIXES:
            if category.startswith(prefix):
                return kind
    return "place"


# Suggestions cover Cebu City, Mandaue and Lapu-Lapu only (spellings vary).
SERVICE_CITIES = frozenset({"cebu city", "mandaue", "mandaue city", "lapu lapu",
                            "lapu lapu city", "lapulapu", "lapulapu city"})


def in_service_city(result: dict) -> bool:
    city = result.get("city")
    return isinstance(city, str) and " ".join(search_tokens(city)) in SERVICE_CITIES


def _suggestion(result: dict) -> dict | None:
    if not in_service_city(result):
        return None
    lat, lon = _coordinate(result.get("lat")), _coordinate(result.get("lon"))
    name = result.get("name") or result.get("address_line1")
    if lat is None or lon is None or not isinstance(name, str) or not name.strip():
        return None
    detail = result.get("address_line2")
    return {
        "source": PROVIDER,
        "location_id": None,
        "name": name.strip(),
        "detail": detail.strip() if isinstance(detail, str) and detail.strip() else None,
        "kind": _kind(result),
        "latitude": lat,
        "longitude": lon,
        "data_attribution": _data_attribution(result),
    }


def suggest_places(text: str) -> ProviderResult:
    """Place suggestions in Cebu City, Mandaue and Lapu-Lapu."""
    words = " ".join(search_tokens(text))
    key = f"{PROVIDER}:suggest:" + hashlib.sha256(words.encode()).hexdigest()
    cached = cache.get(key)
    if cached is not None:
        return ProviderResult("ok", cached)
    outcome = _fetch("autocomplete", {
        "text": text, "limit": SUGGESTION_LIMIT,
        "filter": f"rect:{_config()['SEARCH_RECT']}",
        "bias": f"proximity:{CEBU_CITY_LON_LAT}",
    }, share=_config()["SUGGEST_SHARE"])
    if outcome.status != "ok":
        return outcome
    suggestions = [s for s in (_suggestion(r) for r in outcome.results if isinstance(r, dict)) if s]
    cache.set(key, suggestions, SUGGEST_CACHE_SECONDS)
    return ProviderResult("ok", suggestions)
