# Data sources and rights

Original PadungGo code and documentation use the [MIT License](../LICENSE). Third-party data and assets retain their own terms. Attribution alone does not establish permission to import or redistribute a dataset.

## Source and rights register

| Material | Use and provenance | Rights and limits |
|---|---|---|
| [Cebu DOTC GTFS archive via Transitland](https://www.transit.land/feeds/f-wcb4-cebu~dotc) | Historic transport shapes, stops, routes and timetable values, principally 2014–2017 | Reuse/redistribution permission has not been established. No feed ZIP is bundled. Availability through an archive is not a license or current-service confirmation. This remains a release/data-compliance gap. |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) | Map context, named-place imports and selected route corrections | Open Database License (ODbL); retain attribution and review database/derived-data obligations for the actual use. Map geometry does not establish current operation or safe boarding. |
| [OpenFreeMap](https://openfreemap.org/) | Browser basemap tiles/style | Service and underlying map/font assets have separate terms and attribution. Do not relabel them MIT. |
| [Geoapify](https://www.geoapify.com/) | Optional address labels and extra place suggestions | Provider terms, quotas and underlying-data attribution apply. Not a transport-service verifier. |
| [Supplied LTFRB fare guides](FARE_GUIDE_2026-09-28.md) | Transcribed September 28, 2026 traditional and air-conditioned modern/electric tables | Source access/mapping and applicability limitations are documented separately; the PDFs are not bundled or relicensed. Approximate guide calculation is not a verified fare for every vehicle. |
| [Commuter reports](ROUTE_AVAILABILITY_2026-10.md) | Scarcity/exclusion decisions and correction leads | Dated reports, not regulatory notices, measured frequency, or complete geometry. Avoid personal identifying details. |
| [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) | Optional AI explanation model, hosted by Groq | Apache 2.0 model license; separate hosting terms. Weights are not bundled. |
| Pixelify Sans, Lucide, and software dependencies | Interface font/icons and application libraries | Font and icon packages carry their own OFL/ISC notices; preserve package licenses and check any added assets individually. MIT does not replace dependency licenses. |

GTFS means General Transit Feed Specification, a transport-data format; the format itself does not grant permission for a particular feed. Keep source metadata, rights, observation dates, and derived changes together. Do not mark imported records verified just because import succeeds. See [verification](DATA_VERIFICATION.md).

The dated research below preserves source leads and limitations from earlier reviews. It is not a fresh audit of every external link or a statement that these services operate today. The later [fare review](FARE_GUIDE_2026-09-28.md) supersedes earlier statements that the supplied guide pages had not yet been inspected.

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
A plausible chain through all four services may exceed the current version's one-transfer
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

This October 17 research established published descriptions supporting further investigation
(`documented` in research terms), but no operational database rows were created.
Missing current directional, stop/access and rights evidence prevents trusted routing.

### Code and design references

[JeepMe](https://github.com/RecursiveDev/JeepMe) and [JTransit](https://jtransit.github.io/) were studied as interface and journey-presentation references. This does not establish transport-data accuracy or permission to copy embedded datasets. Any reused code or asset needs its own source, revision, license, required notices, and modification record.

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
