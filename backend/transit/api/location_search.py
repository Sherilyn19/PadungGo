"""Normalise location queries without changing stored location names."""
from __future__ import annotations

import unicodedata


def normalise_query(query: str) -> list[str]:
    decomposed = unicodedata.normalize("NFKD", query.lower())
    characters = []
    for character in decomposed:
        if unicodedata.category(character).startswith("M"):
            continue
        characters.append(character if character.isalnum() else " ")

    tokens = []
    for token in "".join(characters).split():
        if token not in tokens:
            tokens.append(token)
            if len(tokens) == 6:
                break
    return tokens