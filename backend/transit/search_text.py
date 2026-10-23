"""Normalise location text so search ignores case, accents and punctuation.

Acronyms are worked out from each name (never typed into code), so
"University of San Jose-Recoletos" is also found by "usjr" and
"Cebu Normal University" by "cnu".
"""
from __future__ import annotations

import re
import unicodedata

MAX_QUERY_TOKENS = 6

# Small joining words people leave out of acronyms (English, Spanish, Cebuano/Filipino).
ACRONYM_SKIP_WORDS = frozenset({
    "of", "the", "and", "for", "in", "at", "de", "del", "dela", "la", "las", "los",
    "y", "ng", "sa", "san", "sta", "sto",
})
# Words that describe a branch rather than the institution, e.g. "- Basak Campus".
_BRANCH_SEPARATOR = re.compile(r"\s+[-–—]\s+|\s*[(:]")


def search_tokens(text: str, limit: int | None = None) -> list[str]:
    """Lower-case, accent-free, de-duplicated words ("Osmeña Blvd." -> osmena, blvd)."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    characters = []
    for character in decomposed:
        if unicodedata.category(character).startswith("M"):
            continue
        # Apostrophes join a word ("Doctors'") instead of splitting it.
        if character in "'’":
            continue
        characters.append(character if character.isalnum() else " ")

    tokens: list[str] = []
    for token in "".join(characters).split():
        if token not in tokens:
            tokens.append(token)
            if limit is not None and len(tokens) == limit:
                break
    return tokens


def normalise_query(query: str) -> list[str]:
    # A cap keeps a pasted paragraph from becoming dozens of database filters.
    return search_tokens(query, limit=MAX_QUERY_TOKENS)


def split_aliases(aliases: str) -> list[str]:
    """Aliases are typed in Admin separated by commas or new lines."""
    return [a.strip() for a in (aliases or "").replace("\n", ",").split(",") if a.strip()]


def acronyms(name: str) -> list[str]:
    """Likely acronyms of a name, longest form first.

    Both the whole name and the part before a branch label ("- Basak Campus",
    "(Main)") are used, with and without small joining words. "San" is kept
    in the full form so "University of San Carlos" gives both "usc" and "uc".
    """
    found: list[str] = []
    parts = [name, _BRANCH_SEPARATOR.split(name, maxsplit=1)[0]]
    for part in parts:
        words = [w for w in search_tokens(part) if not w.isdigit()]
        if len(words) < 2:
            continue
        keep_san = [w for w in words if w not in ACRONYM_SKIP_WORDS or w in {"san", "sta", "sto"}]
        content = [w for w in words if w not in ACRONYM_SKIP_WORDS]
        every = words
        for chosen in (keep_san, content, every):
            initials = "".join(w[0] for w in chosen)
            if len(initials) >= 2 and initials not in found:
                found.append(initials)
    return found


def build_search_text(name: str, aliases: str = "") -> str:
    """Stored, normalised words of a location's name, aliases and acronyms.

    Kept as a column so the database can filter accent-insensitively and by
    word beginnings without a PostgreSQL extension.
    """
    words = search_tokens(" ".join([name, *split_aliases(aliases), *acronyms(name)]))
    return " ".join(words)
