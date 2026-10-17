# Route Data Verification Standard

Transportation advice must be grounded in reliable **current** service information. A published or historic route is not automatically active today.

## Seven required checks

1. **Identity:** confirm route code, operator, vehicle class and any variants.
2. **Service:** confirm the route currently operates using credible evidence.
3. **Directions:** separately confirm outbound and inbound road paths.
4. **Stops:** validate appropriate boarding, exit and transfer locations, including safe pedestrian access.
5. **Fares:** check applicable vehicle rate, distance-band rules, discounts and effective date.
6. **Evidence:** record publisher, source URL or permitted field observation, verification date, and notes.
7. **Reuse:** confirm the license/permission for importing, displaying and republishing each dataset.

## Internal statuses

| Status | Meaning | Recommended publicly? |
|---|---|---|
| candidate | Found in a directory or research lead | No |
| documented | Published evidence, current operations unconfirmed | No |
| verified | Current routes and directions reviewed and supported | Yes |
| needs_review | Evidence stale, contradictory or disputed | No |

## Data-quality principles

- A route code is not a unique variant identity.
- Stop order and travel direction matter; A→B does not imply B→A is valid on the same path.
- Fare calculation must use **travelled distance by boarded leg**, not a straight line between origin and destination.
- No invented waiting times, live arrival predictions or route coverage claims.
- Document why a route moves from candidate/documented to verified.
- Remove route suggestions from trusted results if supporting evidence becomes invalid.

## Initial research targets (not verified route claims)

Codes to investigate include **01K, 20A, 23D, and 03Q**. These are leads only; neither their operation nor their full routing is established by this document. Verify operator, geographic alignment, transfer feasibility and each direction before importing as verified.

## Suggested evidence entry template

```text
Code / name:
Operator and vehicle type:
Direction and variant:
Streets, stops and terminals:
Source title / publisher / URL:
Source date and date observed:
Coordinates provenance / dataset permission:
Fare rule and effective date:
Conflicting evidence:
Reviewed by / review date:
Status: candidate | documented | verified | needs_review
Notes:
```

## Scope and completeness

The full vision covers locations within and across Cebu City, Mandaue City and Lapu-Lapu City; the MVP uses a smaller verified interconnected subset. 01K, 23D, 20A and 03Q are only the initial research batch, not permanent network limits. Review each direction independently; an unverified reverse direction does not invalidate a verified forward pattern.

Physical-route eligibility and estimate completeness are separate. Missing fare or waiting information remains unknown and does not justify inventing a value. Stop/access or directional evidence missing does exclude the affected guidance. Set record review intervals appropriate to source quality and observed service changes; expired/conflicting support moves affected records to needs_review.
