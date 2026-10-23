"""Merge PadungGo's own locations with provider place suggestions.

Our curated locations come first and keep their record status. Provider
results are labelled with their source; recognising a place says nothing
about which routes serve it.
"""
from __future__ import annotations

from django.db.models import Q

from transit.models import Location
from transit.planner.geo import haversine_m
from transit.search_text import normalise_query, search_tokens, split_aliases

from . import geoapify

CURATED_LIMIT = 6
CANDIDATE_LIMIT = 60
# Provider lookups start at three letters; shorter text matches too much.
MIN_PROVIDER_CHARACTERS = 3
# A provider place this close to a curated one with the same name is a duplicate.
DUPLICATE_DISTANCE_M = 150


def _rank(location: Location, phrase: str, first_word: str) -> int:
    """0 alias exact, 1 name starts with the text, 2 a word starts with it, 3 other."""
    if any(" ".join(search_tokens(alias)) == phrase for alias in split_aliases(location.aliases)):
        return 0
    name_words = " ".join(search_tokens(location.name))
    if name_words.startswith(phrase):
        return 1
    if any(word.startswith(first_word) for word in location.search_text.split()):
        return 2
    return 3


def curated_matches(query: str) -> list[dict]:
    tokens = normalise_query(query)
    if not tokens:
        return []
    candidates = Location.objects.select_related("area")
    for token in tokens:
        # name__icontains also covers rows saved before search_text existed.
        candidates = candidates.filter(Q(search_text__contains=token) | Q(name__icontains=token))
    phrase = " ".join(tokens)
    ranked = sorted(candidates.order_by("name", "id")[:CANDIDATE_LIMIT],
                    key=lambda loc: (_rank(loc, phrase, tokens[0]), loc.name))
    return [{
        "source": "padunggo",
        "location_id": str(loc.id),
        "name": loc.name,
        "detail": loc.area.name if loc.area_id else None,
        "kind": loc.kind,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "status": loc.status,
    } for loc in ranked[:CURATED_LIMIT]]


def _same_place(a: dict, b: dict) -> bool:
    name_a = " ".join(search_tokens(a["name"]))
    name_b = " ".join(search_tokens(b["name"]))
    similar = name_a == name_b or name_a in name_b or name_b in name_a
    return similar and haversine_m(a["latitude"], a["longitude"],
                                   b["latitude"], b["longitude"]) <= DUPLICATE_DISTANCE_M


def _without_duplicates(provider: list[dict], curated: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for place in provider:
        if any(_same_place(place, other) for other in [*curated, *kept]):
            continue
        kept.append(place)
    return kept


def place_suggestions(query: str) -> dict:
    curated = curated_matches(query)
    letters = "".join(search_tokens(query))
    provider_status, provider = "skipped", []
    if len(letters) >= MIN_PROVIDER_CHARACTERS:
        outcome = geoapify.suggest_places(query)
        provider_status = outcome.status
        provider = _without_duplicates(outcome.results, curated)
    return {
        "results": curated + provider,
        "provider": {
            "name": geoapify.PROVIDER,
            "status": provider_status,
            "attribution": [geoapify.PROVIDER_ATTRIBUTION] if provider else [],
        },
    }
