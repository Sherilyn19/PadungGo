"""Merge PadungGo's own locations with provider place suggestions.

Matching ignores case and accents and works on word beginnings, so "u",
"univ san" and "usjr" all find "University of San Jose-Recoletos" as the user
types. Our locations come first and keep their record status. Provider results
are labelled with their source; recognising a place says nothing about which
routes serve it.
"""
from __future__ import annotations

from django.db.models import Q, QuerySet

from transit.models import Location
from transit.planner.geo import haversine_m
from transit.search_text import acronyms, normalise_query, search_tokens, split_aliases

from . import geoapify

CURATED_LIMIT = 8
# Enough matches to rank well even for one typed letter.
CANDIDATE_LIMIT = 400
# Provider lookups start at three letters; shorter text matches too much.
MIN_PROVIDER_CHARACTERS = 3
# A provider place this close to a curated one with the same name is a duplicate.
DUPLICATE_DISTANCE_M = 150
# Our own records with the same name this close together are shown once.
SAME_NAME_DISTANCE_M = 300
# Named places people search for come before plain street/stop names.
_KIND_ORDER = {"school": 0, "mall": 0, "attraction": 0, "landmark": 1, "terminal": 1,
               "transport_hub": 1, "business": 2, "place": 3}


def filter_by_words(queryset: QuerySet, tokens: list[str]) -> QuerySet:
    """Every typed word must start one of the stored words (name, alias or acronym)."""
    for token in tokens:
        queryset = queryset.filter(Q(search_text__startswith=token)
                                   | Q(search_text__contains=" " + token))
    return queryset


def _rank(location: Location, tokens: list[str]) -> tuple:
    phrase = " ".join(tokens)
    name_words = search_tokens(location.name)
    name_text = " ".join(name_words)
    short_forms = [" ".join(search_tokens(a)) for a in split_aliases(location.aliases)]
    short_forms += acronyms(location.name)
    if phrase in short_forms or name_text == phrase or name_text.startswith(phrase + " "):
        match = 0                       # exact alias/acronym ("cnu") or first word(s) ("sm")
    elif name_text.startswith(phrase):
        match = 1                       # name starts with the text: "cebu nor"
    elif len(tokens) == 1 and any(f.startswith(phrase) for f in short_forms):
        match = 2                       # acronym being typed: "usj"
    elif all(any(w.startswith(t) for w in name_words) for t in tokens):
        match = 3                       # words of the name: "san jose"
    else:
        match = 4
    # Within a match level, schools/malls/attractions come before shops and streets.
    return (match, _KIND_ORDER.get(location.kind, 3), len(location.name), location.name)


def curated_matches(query: str) -> list[dict]:
    tokens = normalise_query(query)
    if not tokens:
        return []
    candidates = filter_by_words(Location.objects.select_related("area"), tokens)
    ranked = sorted(candidates.order_by("name", "id")[:CANDIDATE_LIMIT],
                    key=lambda loc: _rank(loc, tokens))
    shown: list[Location] = []
    for loc in ranked:
        # One place mapped twice (e.g. a building and its entrance) is shown once.
        if not any(o.name == loc.name and o.area_id == loc.area_id
                   and haversine_m(o.latitude, o.longitude, loc.latitude, loc.longitude)
                   <= SAME_NAME_DISTANCE_M for o in shown):
            shown.append(loc)
        if len(shown) == CURATED_LIMIT:
            break
    return [{
        "source": "padunggo",
        "location_id": str(loc.id),
        "name": loc.name,
        "detail": loc.area.name if loc.area_id else None,
        "kind": loc.kind,
        "latitude": loc.latitude,
        "longitude": loc.longitude,
        "status": loc.status,
    } for loc in shown]


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
    # Fill the list from the provider only when our own places do not.
    if len(letters) >= MIN_PROVIDER_CHARACTERS and len(curated) < CURATED_LIMIT:
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
