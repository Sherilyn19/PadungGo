"""Normalise location text so search ignores case, accents and punctuation."""
from __future__ import annotations

import unicodedata

MAX_QUERY_TOKENS = 6


def search_tokens(text: str, limit: int | None = None) -> list[str]:
    """Lower-case, accent-free, de-duplicated words ("Osmeña Blvd." -> osmena, blvd)."""
    decomposed = unicodedata.normalize("NFKD", (text or "").lower())
    characters = []
    for character in decomposed:
        if unicodedata.category(character).startswith("M"):
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


def build_search_text(name: str, aliases: str = "") -> str:
    """Stored, normalised words of a location's name and aliases.

    Kept as a column so the database can filter accent-insensitively without a
    PostgreSQL extension, while list pagination still happens in the database.
    """
    words = search_tokens(" ".join([name, *split_aliases(aliases)]))
    return " ".join(words)
