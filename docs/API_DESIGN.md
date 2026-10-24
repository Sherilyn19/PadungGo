# HTTP API

Base path: `/api/v1`. Canonical paths have **no trailing slash**. Request and response bodies use JSON. The public read/planning endpoints need no login; Django Admin is separately authenticated.

## Endpoints

| Method and path | Behavior |
|---|---|
| `GET /health` (outside the base path) | Static liveness |
| `GET /api/v1/health` | Service name, status, spatial mode, forwarding-chain counts |
| `GET /api/v1/locations` | Stored place search and cursor pagination |
| `GET /api/v1/places/suggestions?q=...` | Local matches with optional Geoapify results |
| `POST /api/v1/places/address` | Optional address label for a selected coordinate |
| `GET /api/v1/routes` | Active routes with verified-pattern summaries |
| `GET /api/v1/routes/{id}` | Verified details for an active route; otherwise 404 |
| `POST /api/v1/journeys/plan` | Direct and one-transfer journey search |
| `POST /api/v1/journeys/explain` | Optional AI explanation of an exact selected itinerary |

Health endpoints do not test database connectivity or provider readiness.

## Locations, routes, and pagination

`locations` accepts `q`, `area_id`, `limit`, and `cursor`. Matching normalizes case, accents, punctuation, names, aliases, and generated acronyms; typed words match stored word beginnings. Locations are not restricted to verified status. A location result is not proof of transport coverage.

`routes` accepts `area_id`, `limit`, and `cursor`. Area filtering matches the exact area of stored route stops; it does not expand child areas. Only active Route records are returned, but their `patterns` array contains verified patterns only and may be empty. A documented route can therefore appear in planner results while its detail endpoint returns 404. This difference is current behavior, not evidence that the historical journey is verified.

Both list endpoints return `{"results": [...], "next_cursor": null}`. `limit` defaults to 20 and accepts 1–50. Use the returned last-row identifier as `cursor`; do not construct page numbers. Invalid limits, malformed identifiers, and unknown cursors return 400. Locations order by name/id and routes by code/id. Route codes are not unique identifiers.

Location fields include `id`, `name`, `kind`, `area`, `latitude`, `longitude`, and `status`. Route fields include `id`, `code`, `name`, `vehicle_class`, `operator`, and `patterns`. Route detail adds ordered stop occurrences and verified evidence metadata for its verified patterns.

## Place services

Suggestions trim the query to 100 characters. Local matches come first. Geoapify is consulted only after at least three normalized characters and when local results do not fill the list. Provider results are filtered to named service cities; this is not an exact planner boundary check. Results identify their source and include coordinates; external results have no stored `location_id`. The response also includes `provider.name`, `provider.status`, and attribution.

For address lookup, send `{"latitude": 10.32, "longitude": 123.90}`. The response includes `status`, `label`, the original coordinates, `distance_m`, `reason`, and `attribution`. Status is `resolved`, `no_result`, or `unavailable`. A distant provider match (over 100 metres by default) is not shown. Coordinates are not moved to the found address. Provider unavailability is an HTTP 200 response with a status, rather than a failed journey search. Invalid coordinates return 400.

## Plan a journey

```json
{
  "origin": {"latitude": 10.32263, "longitude": 123.89862},
  "destination": {"latitude": 10.279336, "longitude": 123.855191},
  "max_transfers": 1,
  "limit": 5,
  "sort_by": "fewest_transfers"
}
```

Either endpoint may instead be `{"location_id": "a-real-stored-identifier"}`. Provide one form per endpoint. Coordinate ranges are latitude −90 to 90 and longitude −180 to 180; nonfinite coordinates are invalid. The serializer may coerce numeric strings. Unknown top-level keys are rejected; nested origin/destination objects do not uniformly reject unknown keys. Clients should send only the documented fields.

| Option | Default | Accepted values |
|---|---|---|
| `max_transfers` | 1 | 0 or 1 |
| `limit` | 5 | 1–50 |
| `sort_by` | `fewest_transfers` | `fewest_transfers`, `cheapest`, `fastest`, `least_walking` |

The example is a reproducible coordinate request, not a promise of current service or stable route codes. Return travel uses a second request with endpoints swapped.

### Response structure

The response contains `request_coverage_status`, `reason`, `journey_options`, `ranking`, `warnings`, `coverage`, and `data_updated_on`. The date reflects the stored network version in Manila time, not field-verification freshness; it can be null when no version exists.

Coverage values emitted by the current engine:

- `within_verified_network`: nonempty results under verified-only eligibility. This is a database status claim, not complete geographic coverage.
- `limited_verified_coverage`: empty results or documented-mode results. Documented mode uses this even if an individual result contains only verified patterns.

Empty results also carry `coverage`; it is null when trips exist. Fields: `search_radius_m` (default 500), `origin_has_stop` and `destination_has_stop` (an eligible stop within the radius), `nearest_origin_stop_m` and `nearest_destination_stop_m` (straight-line metres to the nearest eligible stop at any distance, rounded to 100 m, null if none is known), and `reverse_has_trips` (only for `no_journey_within_mvp_limits`: whether the same two places work the other way; null otherwise). It describes coverage only, never invents a stop or route, and the distances are hints, not walking routes. Older clients can ignore it.

Empty-result reasons:

| Literal value | Meaning |
|---|---|
| `same_location` | Endpoints are within about 25 metres |
| `insufficient_verified_data` | No eligible boarding/alighting stop near an endpoint |
| `no_journey_within_mvp_limits` | No result within the current search/data limits; retained legacy API identifier |

`outside_intended_area` exists as a code constant but is not emitted by the current engine. There is no polygon-based rejection. Existing machine-readable identifiers and application warning strings are preserved for compatibility; documentation uses plain-language descriptions.

Each option has a response-local `id`, `transfers`, `has_scarce_ride`, `labels`, ordered `segments`, `fare`, `time`, `evidence`, and `warnings`. Do not persist the option id as a stable journey identity.

Segment modes are `walk`, `ride`, and `transfer_walk`. Ride fields include route/pattern identifiers, code, direction, signboard, boarding/alighting occurrence identifiers and names, sequence numbers, start/end coordinates, optional geometry, distance, duration, fare quotation, guide estimate, availability, verification status, and source identifiers. Geometry uses GeoJSON coordinate order `[longitude, latitude]`. Access/egress walks expose `straight_line_m` but keep actual walking distance/time unknown. Transfer metadata can include a stored distance and duration; inferred same-stop transfers are not field-verified access.

### Fares, times, and ranking

The supported quote in each ride's `fare` has `amount_centavos`, `rule_id`, `passenger_category`, source/effective-date metadata, `status`, and `reason`. The current planner uses regular-passenger quotes. Journey `fare` separates a complete total from a known subtotal; do not display a partial subtotal as the full fare.

`guide_fare_estimate` is separate. When available, it provides `chargeable_km`, `guide_effective_date`, `known_vehicle_type` (currently null), and `amounts_centavos` for traditional/modern × regular/discounted. The interface selects and totals these estimates. Modern here means the supplied air-conditioned modern/electric guide, not every modern vehicle. The estimate rounds each ride distance up to a whole kilometre, limits the table to 50 km, excludes buses, and uses nearest-25-centavo rounding. The supplied source does not establish the fractional-distance rule; see [fare evidence](FARE_GUIDE_2026-09-28.md).

`time.total_seconds`, walking time, and waiting time remain null, and `total_is_complete` is false. Ride durations/subtotals may come from archived schedules. An `estimate_basis` value of `sourced_observation` does not by itself prove a recent observation; consult the source.

`ranking` reports `requested`, `applied`, `warning`, and `scarce_last`. Cheapest requires complete exact fares for all candidates; fastest requires complete times. Otherwise they fall back to fewest transfers. Least walking currently always falls back. Scarce journeys are grouped last after sorting and before the limit, so the entire list is not necessarily globally price-ordered. See [routing](ROUTING_ALGORITHM.md).

## Explain this trip: AI explanation

Send the original `origin`, `destination`, `max_transfers`, and `sort_by`, plus `rides`: one or two objects in travel order, each containing the exact `route_pattern_id`, `board_occurrence_id`, and `alight_occurrence_id` from the plan response. Do not send `limit`, prose, fares, or stop names. Top-level and ride-reference unknown fields are rejected.

The server plans again with up to 50 results and matches the ordered ride identities. A trip no longer present returns 404. A successful HTTP 200 body has `status: "ok"`, `explanation`, `notices`, `ai_generated: true`, and `model`.

Provider failure returns HTTP 200 with `status: "unavailable"`, `reason`, `message`, and `retryable`. Reasons include `not_configured`, `quota`, `rate_limited`, `timeout`, `error`, and `invalid_output`. A rejected answer can include a short `check` code; its rejected text is not returned. The model is given only route codes, stop names and a scarce flag (no fares, times, distances or historic flag), and the accepted text is short and friendly. The server notices stay in the response; a client may show them or, as the web app does, rely on its own on-screen warnings and one short reminder. See [AI configuration and limitations](AI_EXPLANATIONS.md).

## Errors and rate limits

Errors handled by the API use `{"error": {"code": "...", "message": "...", "retryable": false}}`, with optional `fields`. Validation is 400, missing routes/trips 404, request throttling 429, and unexpected API exceptions receive a generic 503. Middleware/server errors outside these views need not use this envelope. Provider unavailability uses the successful-status envelopes described above.

Default limits are 120 general requests/minute, 30 plans/minute, 40 place requests/minute, and 6 explanations/minute. HTTP 429 preserves `Retry-After`. Limits are process-local and depend on proxy identity configuration; they are not strict deployment-wide allowances. Health is unthrottled. See [operations](DEPLOYMENT.md) and [security](SECURITY.md).
