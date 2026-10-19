"""City-sized network performance guard (synthetic, test-only data).

Roughly the size of the Cebu GTFS archive: ~100 routes x 2 patterns, ~60 stops
each, many shared stops with same-stop transfers. The plan must stay fast.
"""
import time

from transit.planner import plan_journeys
from transit.planner.journey_types import (
    Endpoint, Network, PatternData, PatternStopData, PlanRequest, RouteData,
    SegmentData, StopData, TransferData,
)


def _city() -> Network:
    net = Network()
    # 40 x 40 grid of stops, ~110 m apart.
    for i in range(40):
        for j in range(40):
            sid = f"s{i}_{j}"
            net.stops[sid] = StopData(sid, sid, 10.28 + i * 0.001, 123.86 + j * 0.001, status="documented")
    pid = 0
    for r in range(100):
        net.routes[f"r{r}"] = RouteData(f"r{r}", f"R{r}", "", "jeepney", None)
        row, col = r % 40, (r * 7) % 40
        for direction in (0, 1):
            # Alternate horizontal / vertical lines through the grid.
            cells = [(row, k) for k in range(40)] if r % 2 == 0 else [(k, col) for k in range(40)]
            cells += [(min(39, c[0] + 1), c[1]) for c in cells[:20]]
            if direction:
                cells = cells[::-1]
            occ = tuple(PatternStopData(f"p{pid}o{n}", f"s{a}_{b}", n, n * 110, True, True)
                        for n, (a, b) in enumerate(cells))
            segs = tuple(SegmentData(occ[n].id, occ[n + 1].id, 110, 30, "schedule")
                         for n in range(len(occ) - 1))
            net.patterns.append(PatternData(f"p{pid}", f"r{r}", "unspecified", "v", None,
                                            "documented", None, occ, segs))
            pid += 1
    for sid in net.stops:
        net.transfers.append(TransferData(f"t{sid}", sid, sid, 0, None, "documented"))
    return net


def test_city_sized_plan_is_fast():
    net = _city()
    req = PlanRequest(origin=Endpoint(10.281, 123.861), destination=Endpoint(10.315, 123.895))
    start = time.perf_counter()
    res = plan_journeys(net, req, config={"ALLOW_DOCUMENTED": True, "STOP_SEARCH_RADIUS_M": 500})
    elapsed = time.perf_counter() - start
    assert elapsed < 3.0, f"plan took {elapsed:.2f}s"
    assert res.journey_options, res.warnings
    assert len(res.journey_options) <= 5
    keys = [tuple(s.get("route_pattern_id") for s in o["segments"]) for o in res.journey_options]
    assert len(keys) == len(set(keys))
