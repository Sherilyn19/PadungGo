# PadungGo Product Requirements

**Status: proposed requirements; application implementation has not started.**

## Purpose and scope

PadungGo is an open-source, location-to-location public transportation journey
planner for the entire geographic areas of Cebu City, Mandaue City, and Lapu-Lapu
City. Intended journeys include travel within a city, barangay or community and
between cities. No fixed Cebu → Mandaue → Lapu-Lapu sequence is required.

The full vision is progressively comprehensive jeepney and bus coverage. The
hackathon MVP uses a smaller, verified, interconnected subset because a solo
participant must prioritize correctness and completion. Selecting a valid point
inside the intended area does not establish verified transport connectivity.
01K, 23D, 20A and 03Q are the initial research batch, not a fixed network or
verified services. No operational dataset ships in the current repository.

## Problem and users

Students, workers, visitors, new residents and occasional commuters need to know
what to ride, where to board and alight, whether to transfer, likely costs and
durations, and how to return. Local route knowledge is difficult to discover and
can become outdated. Clear evidence and limitations are part of the solution.

## Functional requirements

| ID | Hackathon MVP requirement | Later expansion |
|---|---|---|
| FR1 | Both endpoints accept GPS with consent, selected name-search results, map pins, and predefined landmarks/terminals as appropriate; normalize to coordinates | Broader place catalog and search coverage |
| FR2 | Accept arbitrary valid endpoint pairs in the three-city area, independent of city order; explain unsupported coverage | Progressively comprehensive intra-city and intercity network |
| FR3 | Search verified direct journeys and journeys with at most one transfer | Multiple transfers without redesigning route identity |
| FR4 | Aim for 3–5 genuinely distinct valid alternatives; return zero, one or two when that is all the network supports | More alternatives as connected coverage grows |
| FR5 | Rank by comparable sourced fares, supported duration, transfers and walking; use fastest/cheapest labels only when justified | More preference and accessibility options after evidence supports them |
| FR6 | Explain walking, boarding place, vehicle type, route code/signboard, direction, alighting, transfer walk and next boarding, and final walk | Richer service information |
| FR7 | Show estimated per-ride and total fare, assumptions, currency, rule source and effective date; unknown leg means unknown total | More sourced fare categories and policies |
| FR8 | Separate walking, waiting and riding duration; total only when every required component is supported; otherwise show known subtotal and exclusions | Verified frequency/time-window data; no promise of live ETAs |
| FR9 | Independently search and rank B→A, ideally yielding multiple alternatives; return may differ or be unavailable | Broader directional coverage |
| FR10 | Interactive map shows endpoints, board/alight locations, ride geometry, transfers, supported walking segments and selected alternative | More map layers where useful |
| FR11 | Preserve identity, vehicle class, operator where known, directional variants, ordered stops, geometry, sources, dates, verification history and limitations | Growing catalog with review workflows |

GPS is optional; manually selected destinations remain available after permission
denial. Raw names are not route inputs until resolved. Display text directions
alongside maps. Do not draw an assumed walking route through barriers.

## Data and estimate acceptance rules

Only currently verified directional patterns and eligible stop occurrences may
produce trusted guidance. Candidate, documented, stale or disputed records are
excluded. Verification of outbound service does not establish inbound service.
Route eligibility and individual fare/time completeness are tracked separately:
a verified ride may have an unknown fare or wait, disclosed without invented data.

Unknown amounts and durations are `null`, never zero. Missing fares prevent a
cheapest claim; incomparable total durations prevent an unqualified fastest claim.
No invented routes, schedules, coordinates, fares, waiting estimates or live ETAs.
Third-party evidence and geometry require appropriate reuse rights.

## Example acceptance scenarios

These describe intended behavior, not verified itineraries:

- Sitio Care, Kamputhaw → Pit-os within Cebu City uses the generic planner.
- A Mandaue residential area → a Mandaue shopping center follows the same flow.
- Cebu City → Lapu-Lapu City may return a direct journey, one transfer, or no
  verified result depending on actual evidence.
- Only two valid options yields two options; one itinerary cannot be repeated
  under three ranking labels to imply three alternatives.
- Outbound success with no supported return preserves outbound results and
  explains the return coverage limitation.

## Non-goals for the MVP

Live vehicle tracking, guaranteed arrival times, nationwide coverage, payments,
user accounts, stored commuter GPS history and searches beyond one transfer are
outside the MVP. Broader coverage is a product goal, not current availability.

## Quality, security and privacy

Use the approved React/TypeScript/Vite/Tailwind/shadcn/ui/MapLibre frontend,
Python/Django/DRF backend, Supabase PostgreSQL/PostGIS and Django Admin.
Validate inputs server-side; protect secrets and administrative changes; use
HTTPS, restricted CORS, request limits and redacted logs. Avoid retaining precise
commuter locations. Provide keyboard access, readable contrast, labeled controls,
non-color route labels and mobile-friendly plain-language instructions.

## Definition of success

A demonstrable, source-backed MVP explains real journeys on a limited network,
handles missing coverage honestly, passes direction/transfer/fare/unknown-data
tests, and can be reproduced by a contributor. A synthetic demonstration must be
labeled as such. See [development gates](DEVELOPMENT_ROADMAP.md) and the
[mechanics evidence review](NEXT_STEPS.md); documentation alone is not completion.
