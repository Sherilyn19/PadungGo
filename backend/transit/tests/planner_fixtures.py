"""
Synthetic in-memory network fixtures for ALGORITHM tests only.

These are NOT real Cebu transport data and are NEVER imported into the database
or shown to users. They exist solely to exercise planner correctness, exactly as
docs/ROUTING_ALGORITHM.md section 10 prescribes ("use synthetic route patterns
in tests, clearly separated from real Cebu route data").
"""
from __future__ import annotations

from datetime import date

from transit.planner.journey_types import (
    FarePolicy,
    Network,
    PatternData,
    PatternStopData,
    RouteData,
    SegmentData,
    StopData,
    TransferData,
)


def _stop(sid, name, lat, lon, board=True, alight=True, status="verified"):
    return StopData(id=sid, name=name, latitude=lat, longitude=lon,
                    can_board=board, can_alight=alight, status=status)


def _occ(oid, stop_id, seq, dist, board=True, alight=True):
    return PatternStopData(id=oid, stop_id=stop_id, sequence=seq, distance_along_m=dist,
                           can_board=board, can_alight=alight)


def _seg(frm, to, dist, secs, basis="sourced_observation", sources=("src-1",)):
    return SegmentData(from_occurrence_id=frm, to_occurrence_id=to, distance_m=dist,
                       riding_seconds=secs, estimate_basis=basis, source_ids=sources)


def base_network() -> Network:
    """A small verified network near (10.30, 123.90).

    Stops laid out roughly west->east. Route A (outbound) runs S1->S2->S3->S4.
    Route B (outbound) runs S5->S6->S7. A transfer links S3 (A) -> S5 (B).
    """
    net = Network()
    net.sources = {
        "src-1": {"id": "src-1", "title": "Synthetic test source", "license": "test-only"},
    }
    # Stops (lat, lon). ~0.009 deg lon ~= 1 km at this latitude.
    stops = [
        _stop("S1", "Stop One", 10.300, 123.900),
        _stop("S2", "Stop Two", 10.300, 123.909),
        _stop("S3", "Stop Three (xfer)", 10.300, 123.918),
        _stop("S4", "Stop Four", 10.300, 123.927),
        _stop("S5", "Stop Five (xfer)", 10.3005, 123.918),  # ~55 m from S3
        _stop("S6", "Stop Six", 10.3005, 123.927),
        _stop("S7", "Stop Seven", 10.3005, 123.936),
    ]
    for s in stops:
        net.stops[s.id] = s

    net.routes["R-A"] = RouteData(id="R-A", code="A1", name="Route A", vehicle_class="jeepney", operator="Op A")
    net.routes["R-B"] = RouteData(id="R-B", code="B2", name="Route B", vehicle_class="jeepney", operator="Op B")

    # Route A outbound: S1->S2->S3->S4
    a_occ = [
        _occ("A-o1", "S1", 0, 0),
        _occ("A-o2", "S2", 1, 1000),
        _occ("A-o3", "S3", 2, 2000),
        _occ("A-o4", "S4", 3, 3000),
    ]
    a_segs = [
        _seg("A-o1", "A-o2", 1000, 300),
        _seg("A-o2", "A-o3", 1000, 300),
        _seg("A-o3", "A-o4", 1000, 300),
    ]
    net.patterns.append(PatternData(
        id="P-A-out", route_id="R-A", direction="outbound", variant_key="main",
        signboard="A1 Outbound", status="verified", verified_at="2026-01-01",
        stops=tuple(a_occ), segments=tuple(a_segs), evidence_source_ids=("src-1",),
    ))

    # Route B outbound: S5->S6->S7
    b_occ = [
        _occ("B-o1", "S5", 0, 0),
        _occ("B-o2", "S6", 1, 1000),
        _occ("B-o3", "S7", 2, 2000),
    ]
    b_segs = [
        _seg("B-o1", "B-o2", 1000, 240),
        _seg("B-o2", "B-o3", 1000, 240),
    ]
    net.patterns.append(PatternData(
        id="P-B-out", route_id="R-B", direction="outbound", variant_key="main",
        signboard="B2 Outbound", status="verified", verified_at="2026-01-01",
        stops=tuple(b_occ), segments=tuple(b_segs), evidence_source_ids=("src-1",),
    ))

    # Directed transfer S3 -> S5 (walkable, verified). Reverse NOT added.
    net.transfers.append(TransferData(
        id="T-1", from_stop_id="S3", to_stop_id="S5", distance_m=60,
        duration_seconds=50, status="verified", source_ids=("src-1",),
    ))

    # Verified flat fare for jeepney (synthetic amount, test-only).
    net.fares.append(FarePolicy(
        id="F-1", vehicle_class="jeepney", route_id=None, pattern_id=None,
        passenger_category="regular", currency="PHP", kind="flat",
        policy={"amount_centavos": 1300}, valid_from=date(2026, 1, 1),
        valid_until=None, status="verified", source_ids=("src-1",),
    ))
    return net
