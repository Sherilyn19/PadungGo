"""List-endpoint parameter validation and cursor pagination."""
from __future__ import annotations

import uuid
from typing import Optional

from django.db.models import Q
from rest_framework.exceptions import ValidationError

MAX_LIMIT = 50
DEFAULT_LIMIT = 20


def _parse_limit(request) -> int:
    """Page size: default 20, integer 1–50. Anything else is a 400 error."""
    raw = request.query_params.get("limit")
    if raw is None:
        return DEFAULT_LIMIT
    try:
        value = int(raw)
    except ValueError:
        value = None
    if value is None or not 1 <= value <= MAX_LIMIT:
        raise ValidationError({"limit": [f"Must be an integer from 1 to {MAX_LIMIT}."]})
    return value


def _parse_uuid_param(request, name: str) -> Optional[uuid.UUID]:
    """Optional UUID query parameter; a malformed value is a 400 (not a 503)."""
    raw = request.query_params.get(name)
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        raise ValidationError({name: ["Must be a valid ID."]}) from None


def _paginate(request, queryset, sort_field: str) -> tuple[list, Optional[str]]:
    """Continue after a cursor using the ordered pair (sort_field, id).

    The cursor is the last returned row's ID, rather than a page number.
    """
    limit = _parse_limit(request)
    cursor = _parse_uuid_param(request, "cursor")
    queryset = queryset.order_by(sort_field, "id")
    if cursor is not None:
        anchor = queryset.model.objects.filter(pk=cursor).values_list(sort_field, flat=True)
        if not anchor.exists():
            raise ValidationError({"cursor": ["Unknown cursor."]})
        anchor_value = anchor.first()
        queryset = queryset.filter(
            Q(**{f"{sort_field}__gt": anchor_value})
            | Q(**{sort_field: anchor_value, "id__gt": cursor})
        )
    rows = list(queryset[: limit + 1])
    if len(rows) <= limit:
        return rows, None
    rows = rows[:limit]
    return rows, str(rows[-1].id)