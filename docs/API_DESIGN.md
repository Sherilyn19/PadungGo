# PadungGo API Design

**Proposed contract; no endpoints are implemented.** Backend: Python, Django and
Django REST Framework; Supabase PostgreSQL/PostGIS. All paths below are canonical,
versioned, and have no trailing slash. Configure Django/DRF accordingly; callers
must not depend on POST redirects.

## Scope and conventions

The full vision accepts location-to-location requests within and across Cebu City,
Mandaue City and Lapu-Lapu City, including the same city/barangay. A valid point
does not guarantee verified transit coverage. The MVP searches a smaller verified
interconnected network with direct rides or at most one transfer. 01K, 23D, 20A
and 03Q are initial research leads, never special API cases.

Coordinates are WGS84. Endpoint objects use named latitude/longitude; GeoJSON
uses [longitude, latitude]. Distances are meters, durations seconds, money integer
centavos with currency PHP. IDs are opaque strings. Dates use ISO 8601; timestamps
include a timezone. Unknown values are null, not zero. Display dates using the
commuter's timezone; retain effective dates of fare rules.

## Read endpoints

| Method and path | Input | Public output |
|---|---|---|
| GET /api/v1/health | None | Minimal service status; no secrets or connection strings |
| GET /api/v1/locations | q, optional area_id, limit (default 20; maximum 50), cursor | Matching curated places with id, name, kind, area, latitude, longitude, next_cursor |
| GET /api/v1/routes | Optional area_id, cursor, limit (default 20; maximum 50) | Verified active services and directional pattern summaries, next_cursor |
| GET /api/v1/routes/{id} | Route ID | Identity, vehicle class, known operator, verified variants, signboards, ordered stop occurrences, geometry, evidence dates and limitations |

List parameters for /locations and /routes:

- **`limit`:** an integer from 1 to 50. Any other value returns 400 `invalid_request` with `fields.limit`.
- **`area_id`:** must be an area UUID.
  - On /routes it keeps only routes that stop in that exact area. Child areas are not included.
- **`cursor`:** pass back the `next_cursor` value from the previous response to get the next page. Results are ordered by name for locations and by code for routes, then by id.
- A malformed `area_id` or `cursor`, or an unknown `cursor`, returns 400 with the matching key in `fields`.

> **Behavior change (October 19, 2026 bug fixes).** Earlier builds:
> - silently replaced an invalid `limit` with the default or clamped it;
> - ignored `area_id` on /routes and `cursor` on both endpoints, so "next page" returned the first page again;
> - returned 503 for a malformed `area_id`.

Location search is not a promise of transit availability. General address search
may use a compliant geocoder through a controlled backend adapter; do not pretend
a small curated catalog resolves every possible place name. All four selection
methods ultimately produce coordinates or a known location ID.

Public route details omit internal candidate records and private reviewer notes.
Unknown/unpublished route IDs return 404. Route lists describe verified records,
not live service availability.

## POST /api/v1/journeys/plan

### Request schema

| Field | Type and rule |
|---|---|
| origin | Exactly one of {location_id: string} or {latitude: number, longitude: number} |
| destination | Same type as origin |
| max_transfers | Integer 0 or 1, default 1; larger searches are future work |
| limit | Integer 1–50, default 5. The web app requests 50 so commuters see every valid alternative the search finds (direct options plus up to 40 transfer candidates), ranked most practical first |
| sort_by | fewest_transfers (default), cheapest, fastest, or least_walking |

Both endpoints support all appropriate GPS, resolved name-search, map and curated
inputs without requiring the same input method. Reject ambiguous ID-plus-coordinate
objects, unknown keys and unresolvable IDs. Validate finite numeric latitude
[-90,90] and longitude [-180,180], intended-area membership, bounded request size,
and search limits. Booleans/strings are not numeric coordinates.

Use verified area boundaries for membership; until these exist do not claim that
a bounding rectangle proves exact city inclusion. Boundary data/provider selection
is an open data decision. Identical endpoints produce a successful empty result
with reason same_location, rather than a fabricated vehicle journey.

### Successful response envelope (HTTP 200)

| Field | Meaning |
|---|---|
| request_coverage_status | within_verified_network, limited_verified_coverage, or outside_intended_area |
| reason | null when options exist; otherwise outside_intended_area, insufficient_verified_data, no_journey_within_mvp_limits, or same_location |
| journey_options | Array of distinct ranked option objects; empty is valid |
| ranking | requested sort, applied sort and warning if requested criterion cannot be fairly evaluated |
| warnings | Public limitations and uncertainty messages |

Coverage status describes the dataset relevant to this request, not completeness
across an entire city. Return within_verified_network only if the scoped search
has sufficient reviewed records; otherwise conservatively use
limited_verified_coverage, even when some journeys exist. No options never proves
that no real-world public transport service exists.

### Journey option schema

| Field | Type/content |
|---|---|
| id | Unique within this response; do not imply persisted personal journey history |
| transfers | 0 or 1 |
| labels | Supported labels such as fewest_transfers, cheapest, fastest; one option may have several |
| segments | Ordered walk, ride or transfer_walk objects |
| fare | currency, per_leg, total_centavos nullable, known_subtotal_centavos, total_is_complete, status, reason nullable |
| time | walking_seconds, waiting_seconds, riding_seconds, total_seconds (all nullable), known_subtotal_seconds, total_is_complete, uncertainty_notes |
| evidence | Public source IDs/references, dates and lowercase verification status |
| warnings | Estimate and data limitations |

Each segment includes mode, start/end point, instruction, distance_m nullable,
supported duration_seconds nullable, estimate_basis, geometry nullable and source
references. A ride additionally contains route_id, route_pattern_id, direction,
vehicle_class, operator nullable, route_code/signboard where known,
board_occurrence_id, alight_occurrence_id and their stop names. Its waiting_seconds
is separate from riding duration to avoid counting it twice. Transfer walking
contributes to walking time; any separately modeled overhead must be explicit.

fare.per_leg contains one entry per ride: segment reference, amount_centavos
nullable, rule_id nullable, source references, effective date nullable,
passenger_category, assumptions, status and reason nullable. Each ride segment's
fare object also includes status and reason.

The backend assigns status; clients must not infer it from a numeric amount:

| status | Meaning | Display |
|---|---|---|
| exact | A supported applicable flat fare with no distance-dependent calculation | Amount without an uncertainty label |
| approximate | A supported distance-band calculation using recorded ride distance, which may differ from billable distance | Amount followed by "Approximate" |
| unavailable | No supported amount can be calculated | "Fare unavailable", followed by the supplied reason |

Reasons describe the blocker actually detected. When the specific cause is not
established, use "No supported fare calculation." Reasons are explanatory text,
not stable machine-readable error codes.

Existing verified-rule, evidence, route-or-pattern scope, vehicle-class,
passenger-category and effective-date safeguards remain required. Mixed fleets
do not receive a guessed vehicle-specific fare. Importer defaults do not prove
that a fare guide applies to a vehicle.

Pricing also requires verified RouteEvidence for the specific pattern, in
both strict and historical modes. Documented evidence alone cannot support
a fare, even if the pattern itself is marked verified. This check does not
change historical-route visibility or the public source IDs.

Distance-band quotes additionally require a positive integer max_distance_m
in the rule's policy JSON, supported by the reviewed evidence. It must not be
smaller than base_distance_m. Missing coverage or a distance beyond that limit
produces an unavailable quote. No universal distance limit is inferred.

Above the base distance, a partial increment is unavailable because its charging
policy has not been established. An unresolved monetary rounding tie is also
unavailable. The underlying calculator's existing round-up behavior is not
treated as evidence of an official charging rule. Supported distance-band
amounts remain approximate; this implementation does not establish exact
billable distance.

Sum fares only when every ride has a supported amount. All exact legs produce
an exact total; any approximate leg makes a complete total approximate. Any
unavailable leg makes total_centavos null, total_is_complete false and status
unavailable. Known subtotal is explicitly incomplete and must not be shown as
a complete price. Per-leg reasons remain available in the ride steps.

The status and reason fields are additive, but calculation eligibility is
stricter: a previously numeric amount may now be null. In particular, existing
distance-band rules without supported max_distance_m metadata cannot produce
a quote. This change does not update or activate any production fare rule.
Clients receiving an older response without classification must not assume
that a numeric amount is exact.

For each time category, use null when any required contribution is unknown.
known_subtotal_seconds sums individually supported contributions, including those
in incomplete categories. total_seconds is null unless all required walking,
waiting and riding contributions are known; missing waits are not zero. Return
uncertainty notes with supported estimate assumptions; never label static values
as live ETAs. Zero is allowed only for a confirmed absent/zero component.

Deduplicate using ordered pattern IDs, stop occurrence IDs and transfer links.
Aim for 3–5 valid alternatives; never pad a result to five. Rank cheapest only
when every candidate has a complete exact fare; otherwise fall back and omit
the cheapest label. Eligibility for price comparison considers all candidates
before the result limit is applied. When every candidate has an exact fare,
the cheapest label identifies the lowest fare among the returned options.
Truncating an uncertain candidate cannot restore the label. Approximate
amounts are not ranked as exact prices.
Rank fastest only with comparable supported
complete durations. If the requested criterion cannot fairly order all candidates,
apply fewest_transfers then known walking distance, and disclose the fallback.
Unknown walking distance cannot win least_walking. Keep deterministic ID tie-breaks.

### No-journey example (structural example; no transport assertions)

```json
{
  "request_coverage_status": "limited_verified_coverage",
  "reason": "insufficient_verified_data",
  "journey_options": [],
  "ranking": {
    "requested": "fewest_transfers",
    "applied": "fewest_transfers",
    "warning": null
  },
  "warnings": ["No verified journey is available in the current dataset."]
}
```

## Guide fare estimates

Every ride segment returned by `POST /api/v1/journeys/plan` includes
`guide_fare_estimate`. Walking segments do not include this field.

Example for a 5,900-metre ride:

```json
{
  "status": "available",
  "reason": null,
  "guide_effective_date": "2026-09-28",
  "chargeable_km": 6,
  "known_vehicle_type": null,
  "amounts_centavos": {
    "traditional": {"regular": 1800, "discounted": 1450},
    "modern": {"regular": 2175, "discounted": 1750}
  }
}
```

The example is the value of `guide_fare_estimate`, not a complete segment.

### Calculation and scope

Rates and printed tables are recorded in
[the fare-guide evidence document](FARE_GUIDE_2026-09-28.md).

- All amounts are integer PHP centavos.
- Each ride uses its own distance, rounded up to whole kilometres under
  the owner's estimate policy. This fractional-distance policy is not
  stated in the supplied guides.
- The first four kilometres use the base amount. Additional whole
  kilometres use the printed increment. Round the resulting amount once
  to the nearest 25 centavos using integer arithmetic.
- Traditional base/increment: regular 1400/200; discounted 1120/160.
- Aircon modern/electric base/increment: regular 1700/240;
  discounted 1360/192.
- `discounted` is the printed Student / Elderly / PWD column, used for
  student, senior and PWD selections. Never calculate it from the
  rounded regular amount or apply another discount.
- `modern` refers only to aircon modern and electric PUJ. It does not
  establish coverage for non-aircon modern vehicles.
- Existing documented route distances may support estimates. Estimate
  availability does not verify a route, distance, vehicle or fare.
- `known_vehicle_type` is always null in this implementation. Neither
  route labels nor matching verified fare rules establish guide eligibility.
- The endpoint uses the server's current date for guide eligibility.

### Unavailable estimates

An unavailable estimate retains all six keys. `status` is `unavailable`;
`chargeable_km`, `known_vehicle_type` and `amounts_centavos` are null.
`guide_effective_date` remains `2026-09-28`.

Reasons are evaluated in this order:

| Reason | Condition |
|---|---|
| `missing_distance` | Missing, non-integer, boolean, zero or negative distance |
| `beyond_guide_range` | Chargeable distance exceeds 50 km |
| `not_puj` | Vehicle class is `bus` |
| `guide_not_in_effect` | Query date is before September 28, 2026 |

Within the current vehicle-class enum, `jeepney`, `modern_puv` and `mixed`
receive both guide options when distance and date are supported. Their
labels never automatically select an option.

### Consumer behavior and verified fares

The existing segment `fare`, journey `fare`, and ranking behavior remain
unchanged. Guide estimates do not populate verified totals or establish
eligibility for cheapest-fare ranking.

Consumers preserve an existing exact or approximate verified quote for
its quoted passenger category. They must not reuse that quote for a
different category or discount it again. This change does not add
passenger-category request support or additional verified quotes.

For guide-based rides, consumers select the appropriate vehicle and fare
column. “Not sure” uses the lower and higher guide amounts. Journey ranges
sum the per-ride lower bounds and upper bounds separately, using integer
centavos. Show a complete total only when every ride has a supported amount.

Display guide-based amounts as Estimated, with exactly two decimal
places. For an unsupported ride, show a brief message such as
“Ask the driver for this ride's fare.” The guide range represents these
two supplied guide options, not every possible vehicle fare.

## Network data update date

Successful `POST /api/v1/journeys/plan` responses include the top-level
field `data_updated_on`: a `YYYY-MM-DD` string or null, including responses
with no journey options.

The value is the singleton `NetworkDataVersion.updated_at` converted to
Asia/Manila, then formatted as a date. For example,
`2026-10-17T17:00:00Z` becomes `"2026-10-18"`.
If the singleton row does not exist, the value is null.

This lookup does not create or modify the row. Other response fields
and error responses remain unchanged.

This network-wide timestamp refreshes when cache invalidation runs,
including after Django Admin saves and completed GTFS imports.
It is not a field-verification date or a separate update date for each
route. Direct SQL and bulk updates require explicit cache invalidation.

## Imported route-name cleanup

Future GTFS imports remove trailing `(Name missing)` and `(nodata)`
suffixes case-insensitively. Meaningful parentheses such as `(Ibabao)`
remain intact. Placeholder-only names retain existing fallback behavior,
and cleaning a descriptive name does not turn it into a route code.

Existing stored records are not rewritten. This change does not authorize
deleting sources or re-importing production data.

## Independent return query

Send a second POST /api/v1/journeys/plan with origin=B and destination=A.
All validation, candidate generation, estimates, deduplication and ranking run
again. Return may use different stops, directions, transfers and fares, yield
multiple alternatives, or fail independently. There is no separate /return
endpoint in this canonical MVP contract.

## Error contract

Errors use {error: {code, message, fields?, retryable}} with safe messages.

| HTTP status | Behavior |
|---|---|
| 400 | invalid_request: malformed endpoint, unknown location ID, invalid preference/coordinate or limits |
| 404 | not_found for unknown/unpublished route-detail resources |
| 429 | rate_limited; Retry-After where available |
| 503 | service_unavailable for database/provider failure preventing a trustworthy answer; distinguish from no-results |
| 200 with empty options | Valid request without a supported journey, including outside intended area |

Provider failure may yield qualified partial estimates only if the route/access
itself remains verified. It must not silently become evidence that no route exists.

## Security and contract verification

Use DRF serializers, parameterized ORM/geospatial queries, throttling, bounded
candidate counts, HTTPS, allowed hosts and exact frontend CORS origins. Admin
writes require authenticated authorization and CSRF protection. Public access
must not grant direct Supabase administrative access. Keep credentials server-side
and remove precise coordinates from logs; no stored commuter GPS history in MVP.

Before release test response schemas, coordinate/ID validation, unknown propagation,
same-city requests, directionality, independent returns, one-transfer cap, empty
results, fallback ranking, private-field exclusion and safe dependency failures.
See [routing](ROUTING_ALGORITHM.md) and [database](DATABASE_DESIGN.md).

## AI explanation endpoint

The AI feature explains a completed planner response. It receives a selected
journey option, public evidence fields, warnings and the user's question. It has
no authority to search unverified routes, change fares/directions or write route
records. Responses preserve the source itinerary and uncertainty labels. The
exact endpoint path is deferred until implementation design.
