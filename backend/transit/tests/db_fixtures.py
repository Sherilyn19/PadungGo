"""
Build a small VERIFIED network directly in the DB for API-level tests.

As with the planner fixtures, this is synthetic test-only data and is never
shipped or exposed as real commuter guidance.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from transit.models import (
    DataSource,
    FareRule,
    PatternStop,
    Route,
    RoutePattern,
    RouteEvidence,
    RouteSegment,
    Stop,
    TransferConnection,
)


def build_verified_network():
    src = DataSource.objects.create(
        title="Synthetic test source", collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        license="test-only",
    )
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def stop(name, lat, lon):
        return Stop.objects.create(name=name, latitude=lat, longitude=lon,
                                   status="verified", verified_at=now, source=src)

    s1 = stop("Stop One", 10.300, 123.900)
    s2 = stop("Stop Two", 10.300, 123.909)
    s3 = stop("Stop Three", 10.300, 123.918)
    s4 = stop("Stop Four", 10.300, 123.927)
    s5 = stop("Stop Five", 10.3005, 123.918)
    s6 = stop("Stop Six", 10.3005, 123.927)
    s7 = stop("Stop Seven", 10.3005, 123.936)

    ra = Route.objects.create(code="A1", name="Route A", vehicle_class="jeepney", operator="Op A")
    rb = Route.objects.create(code="B2", name="Route B", vehicle_class="jeepney", operator="Op B")

    pa = RoutePattern.objects.create(route=ra, variant_key="main", direction="outbound",
                                     signboard="A1 Outbound", status="verified", verified_at=now)
    pb = RoutePattern.objects.create(route=rb, variant_key="main", direction="outbound",
                                     signboard="B2 Outbound", status="verified", verified_at=now)

    def occ(pat, st, seq, dist):
        return PatternStop.objects.create(pattern=pat, stop=st, sequence=seq, distance_along_m=dist)

    a1, a2, a3, a4 = occ(pa, s1, 0, 0), occ(pa, s2, 1, 1000), occ(pa, s3, 2, 2000), occ(pa, s4, 3, 3000)
    b1, b2, b3 = occ(pb, s5, 0, 0), occ(pb, s6, 1, 1000), occ(pb, s7, 2, 2000)

    for frm, to, d in [(a1, a2, 1000), (a2, a3, 1000), (a3, a4, 1000)]:
        RouteSegment.objects.create(pattern=pa, from_occurrence=frm, to_occurrence=to,
                                    distance_m=d, riding_seconds=300, estimate_basis="sourced_observation",
                                    source=src)
    for frm, to, d in [(b1, b2, 1000), (b2, b3, 1000)]:
        RouteSegment.objects.create(pattern=pb, from_occurrence=frm, to_occurrence=to,
                                    distance_m=d, riding_seconds=240, estimate_basis="sourced_observation",
                                    source=src)

    RouteEvidence.objects.create(pattern=pa, source=src, reviewed_at=now, reviewer="tester", status="verified")
    RouteEvidence.objects.create(pattern=pb, source=src, reviewed_at=now, reviewer="tester", status="verified")

    TransferConnection.objects.create(from_stop=s3, to_stop=s5, distance_m=60,
                                      duration_seconds=50, status="verified", source=src)

    FareRule.objects.create(vehicle_class="jeepney", kind="flat",
                            policy={"amount_centavos": 1300}, valid_from=date(2026, 1, 1),
                            status="verified", source=src)

    return {"src": src, "routes": {"A": ra, "B": rb}, "stops": {s.name: s for s in [s1, s2, s3, s4, s5, s6, s7]}}
