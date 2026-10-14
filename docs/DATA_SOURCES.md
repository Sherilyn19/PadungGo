# Transportation and Mapping Data Sources

**This is a research checklist, not confirmation that any feed is current, complete, or licensed for redistribution.**

| Potential source | Possible use | Verify before use |
|---|---|---|
| LTFRB official communications | Route regulations and fare policies | Effective date, exact vehicle class, rounding and exceptions |
| Cebu LGUs / transport offices | Terminals, authorized boarding places, route plans | Whether plan reflects current operations |
| Cebu GTFS archive on Transitland | Historic shapes, stops and routes | Archived service dates; access and redistribution terms |
| OpenStreetMap | Roads, map context, some transit locations | ODbL attribution / derived database obligations and tile policy |
| Operator schedules / signs | Route operation and service frequencies | Current operation and permission to republish |
| Permitted field observations | Boarding locations and directional operation | Timestamp, reviewer and scope of observation |

Useful starting URLs:
- https://www.ltfrb.gov.ph/
- https://www.transit.land/feeds/f-wcb4-cebu~dotc
- https://www.openstreetmap.org/

## Import rules

1. Record licensing and source attribution **before** storing a third-party dataset in the public repository.
2. Keep `data/candidate` and `data/verified` separate.
3. Do not assume a source is accurate for 2026 merely because its webpage was recently refreshed.
4. Never describe historical or synthetic data as current, verified commuter guidance.
5. The MIT code license does **not** automatically cover third-party route databases or map tiles.
