"""Per-visitor request limits for endpoints that are expensive or use a paid quota.

Who is the visitor? Behind Render the connecting address (REMOTE_ADDR) is
Render's own proxy, and the real client is only in the X-Forwarded-For header.
That header is written by every proxy on the way, but a client can also send
its own copy, which ends up at the LEFT of the chain. Each trusted proxy
appends the address it received the request from, so the entry that the
outermost trusted proxy appended is the real client, and entries to its left
are untrusted. DRF's default (NUM_PROXIES unset) uses the whole header text as
the identity, which both lets anyone dodge a limit by adding junk and splits
one visitor into many (the proxy addresses change between requests).

TRUSTED_PROXY_HOPS (setting, env DRF_NUM_PROXIES) is how many proxies append to
X-Forwarded-For. 0 means "trust none": only REMOTE_ADDR is used.

Counters live in each web worker's memory. With several workers a visitor can
use up to workers x rate, and a restart clears them. That is acceptable here
because the quota that costs money is capped separately by shared database
counters (ProviderUsage), which every worker and restart agrees on.
"""
from __future__ import annotations

import ipaddress

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle

UNKNOWN_CLIENT = "unknown"


def _normalise(address: str) -> str | None:
    """A valid IP as text. IPv6 is grouped by /64, since one home line gets a whole /64."""
    try:
        ip = ipaddress.ip_address(address.strip())
    except ValueError:
        return None
    if ip.version == 6:
        return str(ipaddress.ip_network(f"{ip}/64", strict=False))
    return str(ip)


def client_identity(meta: dict, hops: int) -> str:
    """The visitor's address, or the connecting address if the header cannot be trusted."""
    connecting = _normalise(meta.get("REMOTE_ADDR", "")) or UNKNOWN_CLIENT
    if hops <= 0:
        return connecting
    chain = [part for part in meta.get("HTTP_X_FORWARDED_FOR", "").split(",") if part.strip()]
    # Fewer entries than trusted proxies: the request did not come through them,
    # so the header is not ours to believe. Share the connecting address's bucket.
    if len(chain) < hops:
        return connecting
    return _normalise(chain[-hops]) or connecting


class ClientRateThrottle(AnonRateThrottle):
    """AnonRateThrottle that identifies visitors with client_identity()."""

    def get_ident(self, request):
        return client_identity(request.META, settings.TRUSTED_PROXY_HOPS)


class GeneralRateThrottle(ClientRateThrottle):
    """Every API request. Rate comes from DRF_ANON_THROTTLE (default 120/min)."""

    scope = "anon"


class PlanRateThrottle(ClientRateThrottle):
    """Trip planning. Rate comes from DRF_PLAN_THROTTLE (default 30/min)."""

    scope = "plan"


class PlacesRateThrottle(ClientRateThrottle):
    """Place suggestions and addresses. Rate comes from DRF_PLACES_THROTTLE (default 40/min)."""

    scope = "places"


class ExplainRateThrottle(ClientRateThrottle):
    """AI trip explanations. Rate comes from DRF_EXPLAIN_THROTTLE (default 6/min)."""

    scope = "explain"
