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

## Pilot scope clarification

The full vision covers locations within and across Cebu City, Mandaue City and Lapu-Lapu City. The MVP uses a smaller verified interconnected subset. 01K, 23D, 20A and 03Q are the initial research batch, not permanent limits or verified coverage. No October 14 research report is available in the supplied files; no historical findings or source values have been changed.

## Route-directory research — October 17, 2026

**Desktop research only. No route has been promoted to verified.** Retrieval date
is not an observation date or proof of current service. These notes summarize
research leads, not a reproduced route database or navigable itinerary.

### Source register

| ID | Reference | Observed source metadata | Use and limitations |
|---|---|---|---|
| CT-01 | [CommuteTour Cebu route directory](https://ph.commutetour.com/travel/transport/jeep/cebu-city-jeep-route-code/) | Page displays January 16, 2026 update; fare section refers to 2023 | Route-code, place and directional research leads; update date does not verify each service. No explicit reusable-data license established in this review |
| CJ-01 | [Cebu Jeepneys directory](https://cebujeepneys.weebly.com/jeepney-routes.html) | No route-level observation/update date established in reviewed text | Links to the four pilot codes; footer attributes maps to John Mercado Lee under CC BY-NC 3.0 |
| CC-01 | [Creative Commons BY-NC 3.0 terms](https://creativecommons.org/licenses/by-nc/3.0/deed.en) | License terms inspected | Attribution and noncommercial restrictions apply to covered material; do not relabel maps/derived assets as MIT. Review exact asset scope and embedded map-provider terms before reuse |
| PIA-01 | [Government notice on updated fare matrices](https://pia.gov.ph/news/luzon/ncr/ltfrb-reminds-puv-operators-drivers-to-display-updated-fare-matrix) | Published September 28, 2026 | Reports updated PUV fare matrices and directs users to LTFRB. It does not establish a specific fare for each Cebu vehicle/pattern |
| LTFRB-01 | [LTFRB fare-rates page](https://ltfrb.gov.ph/fare-rates/) | Retrieval returned HTTP 403 in this review | Current applicable matrix could not be inspected through this URL; do not infer rates from the failed request |

### Initial four-code comparison

CT-01 describes these endpoint associations: 01K Urgello–Parkmall, 03Q
Ayala–SM City Cebu, 20A Ayala–Mandaue, and 23D Parkmall–Opon. Its
direction sections supply investigation leads; they do not establish eligible
boarding locations or independently confirmed current operation.

| Code | Additional directory evidence | Unresolved issue and next check |
|---|---|---|
| 01K | [CJ 01K](https://cebujeepneys.weebly.com/01k.html) describes Urgello/Parkmall travel with different outbound/return street sequences | Confirm current terminal positions, streets, vehicle/operator identity and boarding/alighting permissions; do not reverse a single path |
| 03Q | [CJ 03Q](https://cebujeepneys.weebly.com/03q.html) names Ayala Center Cebu to SM City Cebu; body relies heavily on an embedded map | Confirm both directions and exact accessible boarding locations; a heading is insufficient to build ordered stop occurrences |
| 20A | [CJ 20A](https://cebujeepneys.weebly.com/20a.html) distinguishes even/odd plate-number variants with different paths | Investigate whether this distinction still operates and how passengers recognize it; do not collapse the code into one universal pattern |
| 23D | [CJ 23D](https://cebujeepneys.weebly.com/23d.html) also names MI-23A and describes distinct directional paths | Treat alias equivalence as an unverified claim; confirm current code/signboard, operator, bridge alignment and terminal access before merging identities |

The 20A detail is a difference in source granularity, not proof either directory is
wrong. Matching names across two directories also do not prove independent
corroboration: their underlying sources may overlap. No current operator/LGU
confirmation or field observations were established in this pass.

### Connectivity hypotheses, not commuter instructions

Shared place names suggest checking 01K/23D around Parkmall, 01K/03Q around
SM City Cebu, and 03Q/20A around Ayala. These are research hypotheses only.
Nearby terminals may have different bays, road sides, restrictions or unsafe
crossings. Verify each directed pedestrian connection before adding a transfer.
A plausible chain through all four services may exceed the MVP's one-transfer
limit; do not promise every pair is reachable merely because the graph connects.

The four codes remain an initial batch. Future same-city and intercity research
can add routes without changing planner logic. No full three-city coverage is
established here.

### Evidence required before promotion

For each proposed directional pattern, collect current service/operator evidence,
dated signboard/terminal observations where permitted, ordered stop occurrences,
legal boarding/alighting points, sourced geometry and reuse rights. Separately
verify transfer walks and direction-specific access. Preserve who observed/reviewed
what and when, conflicting claims, and the exact evidence scope.

Fare approval requires the applicable current LTFRB rule/matrix, vehicle class,
geographic applicability, effective date, distance bands, rounding and discounts.
Do not copy directory prices into the fare service. Waiting estimates require
separate frequency/timetable evidence. No fare amount, coordinate, headway or
route geometry was imported by this research.

The pilot now has published descriptions supporting further investigation
(`documented` in research terms), but no operational database rows were created.
Missing current directional, stop/access and rights evidence prevents trusted routing.

### Reference and selective-reuse policy

The owner chose references first: study JeepMe's map interactions/structure/route
selection and JTransit's instructions/transfers/trip presentation. Build PadungGo's
core using the approved stack, direction-aware planner, evidence records and
independent return search.

Evaluate small code reuse only when it saves time. Record the exact upstream
file/commit, license and required notices, purpose, local modifications and tests.
A repository code license does not establish rights or accuracy for every embedded
dataset/map. Route catalogs remain research leads requiring separate verification.
No third-party code or map assets have been copied.

## Suroy reference review — October 17, 2026

**SU-01:** [Suroy Cebu City Jeepney Guide 2026](https://suroy.ph/cebu-city-jeepney-guide-2026/),
by Migs Alcantara. Header dates: published August 11, updated September 19, 2026;
the body separately says updated August 10. Preserve this metadata inconsistency.

Useful for route-code/landmark leads and plain-language boarding guidance. Its
01K summary emphasizes central Cebu–SM, while the earlier directories describe
Parkmall; this may be abbreviated coverage, not proof of a changed endpoint.
Its 03Q summary includes Mabolo/Ayala/SM. It does not resolve 20A or 23D.

The fare section says prices were checked in August and that a proposed increase
remained suspended. This predates PIA-01's September 28 update notice; do not use
SU-01 to establish current fares. Resolve actual applicability with the official
Cebu/vehicle-class matrix. No prices were imported.

Treat as a secondary reference, not verified operational data. No reusable-content
license was established from the reviewed page. Link and summarize; do not copy
its route table, photographs or map assets into the project.
