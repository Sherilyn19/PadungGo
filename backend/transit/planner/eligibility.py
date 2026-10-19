"""Shared status gate for network loading and journey search."""
from __future__ import annotations


def allowed_statuses(allow_documented: bool) -> frozenset[str]:
    """Documented records are eligible only when explicitly enabled."""
    return frozenset({"verified", "documented"} if allow_documented else {"verified"})