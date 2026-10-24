# Journey planning behavior

The planner is deterministic Python code. It searches stored directional route patterns; AI only explains a selected result afterward.

## Eligibility and network loading

Only active routes participate. By default, eligible records must be `verified`; `PLANNER_ALLOW_DOCUMENTED=True` additionally admits documented historical records and emits notices. Candidate and needs-review records are excluded by eligibility checks. Boarding/alighting switches on both physical stops and pattern occurrences matter.

The loader assembles an in-memory network from the database, with a per-process cache and shared version invalidation. PostGIS fields do not mean the current search runs spatial SQL. The implementation uses Python distance calculations over the loaded network.

A verified status is not an automatic source audit. Review dates do not automatically expire records, and no exact city polygon is enforced. These are gaps between a verification-first policy and automatic enforcement.

## Search

1. Validate endpoints, transfer count, result limit, and sort choice. Endpoints within about 25 metres produce `same_location`.
2. Find eligible nearby boarding and alighting stops using straight-line distance (default radius 500 metres).
3. For each usable directional pattern, select a usable nearest boarding occurrence and a later alighting occurrence. Occurrence identity permits a pattern to revisit the same physical stop without reversing travel order.
4. If one transfer is allowed, enumerate connections through eligible directed transfer records between patterns. The search skips patterns already offering a direct option, keeps selected short ride combinations, and retains up to 40 transfer candidates after enumeration.
5. Assemble segments, fare/time/evidence metadata, deduplicate by ordered ride and transfer identity, rank, group scarce journeys last, and apply the requested limit of up to 50.

This is a heuristic search, not exhaustive enumeration of all journeys or a proof of global optimality. The 40-candidate retention limit is not a bound on all enumeration work. A missing result means the stored network and search did not find an option, not that no service exists.

## Ranking

Fewest transfers orders by transfer count, then ride distance, known straight walking distance, and stable identity. Cheapest is used only when every candidate has a complete exact fare. Fastest requires complete times; current assembly does not produce them. Least walking always falls back because straight lines cannot establish the shortest walkable path. `ranking` discloses the applied choice and fallback warning.

After sorting, journeys containing any scarce ride are placed last, preserving order within each group. The limit is applied afterward. “Not flagged” means there is no stored scarcity flag, not verified frequent service. Labels compare available results; they do not establish optimality across an entire city network.

## Distances, durations, and fares

Ride distance comes from cumulative distance along stored stop occurrences. Ride time sums available segment durations; missing segments make a complete ride duration unknown. Historical timetable values may be present and must not be described as current live observations.

Access/egress walking is a straight-line estimate. Complete walking, waiting, and journey time remain unknown. The known time subtotal is riding only; it is not a full trip estimate.

There are two fare paths:

- **Supported quotation:** validates fare rule scope, dates, vehicle applicability, verification/evidence, and supported distance policy. Flat quotes can be exact; supported distance quotes remain approximate. Unsupported partial increments or ambiguous rounding are withheld.
- **Guide estimate:** uses the supplied September 28, 2026 traditional and air-conditioned modern/electric tables. Each positive integer ride distance is rounded up to a kilometre, up to 50 km; the resulting amount is rounded to 25 centavos. Buses are excluded. This fractional-distance rule is an application estimate assumption, not established official policy. The interface selects passenger/vehicle values; the backend does not infer the actual vehicle subtype.

Guide estimates do not become verified fare rules and do not justify cheapest ranking. The fixed guide has no automatic supersession detection. See [fare evidence](FARE_GUIDE_2026-09-28.md).

## Return and failure behavior

A return journey is a new search with swapped endpoints. It may use different patterns, stops, or transfers. Missing reverse data is not filled by reversing geometry.

Empty results use `same_location`, `insufficient_verified_data`, or the legacy literal `no_journey_within_mvp_limits`. The `outside_intended_area` constant is currently unused. See the [API contract](API_DESIGN.md) for exact output fields and [roadmap](ROADMAP.md) for future work.
