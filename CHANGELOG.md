# Changelog

Significant project changes. Earlier dated entries describe their historical state, not necessarily current behavior.

## Documentation review — 2026-10-24

- Replaced the event-branded overview with a general project README and useful license/CI/contribution badges.
- Organized commuter instructions, setup, architecture, database, API, data rights, AI, security, and deployment guides around the current implementation.
- Retired obsolete personal schedules and pre-implementation checklists while retaining dated source and fare evidence.
- Separated competition alignment from the public product overview; recorded the public repository and participant-confirmed completed video/form submission.
- Documented historic data, unresolved feed permissions, approximate fare assumptions, incomplete timing, heuristic search, process-local limits, and AI fare-selection differences.
- Recorded verification results and limits in [the October 24 review](docs/REVIEW_2026-10-24.md). No application behavior, license, data, or deployment changed in this documentation pass.

## Unreleased

- Rate limits now work in production (#59, #60, #61). They had never applied: the
  per-visitor limits used the whole `X-Forwarded-For` text as the identity, and
  behind Cloudflare and Render that text changes on every request. Visitors are now
  identified by the third address from the right (the proxies' own entry), anything
  a client writes on the left is ignored, and IPv6 is grouped by /64. Verified live:
  HTTP 429 after the limit, rotating fake headers do not escape, allowed again after
  the window. `/api/v1/health` now reports `forwarded_chain_length` and
  `trusted_proxy_hops` (counts only) so the setting can be checked from outside.
- AI explanation: four fixes found by testing the live API: unnamed stops (#53),
  ordinary wording such as "10-minute ride" (#56), numbers written as words (#57)
  and Unicode dashes in "field-verified" (#58). It never says a route is "not
  scarce" or common (#62), because an unflagged route only means no report exists.
- The sort picker is hidden while the planner can only order by fewest transfers
  (#63). Cheapest, Fastest and Least walking always fell back to it. The API still
  accepts all four.
- Route 03K is Scarce again (updated commuter report, Oct 24).
- New demo journey for the video: Ayala Center Cebu to Colon Obelisk and back (17D to
  42D no longer works because 42D is excluded). Site address is now
  https://padung-go.app.

- Fix: "Explain this trip" rejected true quantities written as words ("eight
  minutes"), which the prompt itself asks for. Spelled-out numbers are now
  converted to digits and checked against the planner's facts like any other
  number, so true values pass and invented ones ("forty minutes", "an hour",
  "half an hour") are still rejected. Found from the failed-check code on the
  live API (`invented_quantity`).

- Fix: "Explain this trip" no longer rejects ordinary wording. Accepted now:
  "10-minute ride", "1 transfer" (the trip's own transfer count), "->" arrows,
  "no guarantee", "has not yet been verified", and more ways of saying a fare or
  wait is unknown. Invented prices, times, numbers, routes and verification
  claims are still rejected. An `invalid_output` response now includes `check`,
  the code of the failed check (never any answer text).

- Fix: "Explain this trip" rejected real trips whose stops have no name in the
  imported feed ("Unnamed stop (feed id …)"), because the answer had to repeat
  that placeholder. Such stops are now described as "the stop shown on the map"
  (like the app screen), and same-stop transfers are flagged. Found by testing the
  live API. Rejection reasons are now logged at WARNING so they appear in
  Render's logs (reason code only, never trip or model text).

- "Explain this trip" (AI): a button in Trip details asks `openai/gpt-oss-20b`
  (OpenAI, Apache 2.0 open weights, hosted by GroqCloud) for a short plain-English
  explanation of the selected trip. New endpoint `POST /api/v1/journeys/explain`;
  the server plans again and finds the trip from opaque ride IDs, so clients
  cannot supply route facts. The model gets minimal facts (no coordinates), its
  answer is checked against the planner's facts before display, and timeouts,
  quota or bad answers show an "unavailable" state without affecting the
  itinerary. Per-visitor throttle `DRF_EXPLAIN_THROTTLE` (6/min), a daily provider
  cap, and caching. Disabled until `AI_API_KEY` is set. Initially unverified against the live hosted model; later October 24 checks returned real explanations (see the review record). No migration; ride segments of the plan response are
  now typed with their `route_pattern_id` / occurrence IDs on the frontend.

- Trip planning is now limited per visitor (30 searches a minute, adjustable with
  DRF_PLAN_THROTTLE). The old setting was attached to the wrong object and never
  applied. Over the limit, the app answers 429 with a plain message and Retry-After.

- Smarter place search (migration 0007). Suggestions start from the first
  letter, match word beginnings and automatically worked-out acronyms (e.g.
  usjr, cnu, mcia) without hardcoding any place. Admin can import named places
  in Cebu City, Mandaue and Lapu-Lapu from OpenStreetMap; Geoapify results are
  limited to those three cities.

- Readable addresses and better place search (migration 0006). After "My
  location" or a map pin, the app shows the address found through Geoapify, or
  "Selected location — address unavailable" with coordinates; the exact point
  is still used for planning. Suggestions ignore case and accents, match Admin
  aliases (e.g. CTU on each separately named campus) and add Geoapify map
  results, labelled separately. The key stays on the server; quotas are guarded
  by caching, throttling and a shared daily counter.

- Route availability (#35 backend, plus frontend): Admin can mark a route
  Scarce (`Route.service_availability`, migration 0005). Trips with a
  Scarce ride are listed after other trips before the result limit is
  applied, and the chosen sort still applies within each group. The app
  shows a "Scarce" badge on those rides and briefly explains its meaning.
  No waiting times are shown. Older responses without these fields show no
  badge. Routes excluded from suggestions still use `active = False`, with
  their records kept.

- Refresh the network update timestamp during cache invalidation so
  journey responses reflect Admin saves and completed GTFS imports.
  Added a regression test for route saves and Manila date conversion.

- Clean trailing placeholder suffixes from names on future GTFS imports,
  preserving route codes and meaningful parentheses. Add read-only
  `data_updated_on` to journey-plan responses using the stored network
  timestamp converted to Asia/Manila, or null when absent.

### Friendlier wording, Bisaya messages and new headers — October 22, 2026

- Get-off step now says "Hapit na! Andam na sa pagnaog." The yellow route
  notice is replaced by "Padayon lang! Basaha ang karatula o pangutan-a ang
  drayber sa dili pa ka mosakay." plus the route-data update date when the
  server provides `data_updated_on`.
- Distances spell out "meters" (e.g. "224 meters", "547+ meters"); long
  rides read "1 hr 15 min". Map legend says "Walk".
- Route names hide the feed placeholder "Name missing" (e.g. "LABANGON
  (Name missing)" shows as "Labangon"; a placeholder-only name is hidden and
  the route code still shows). Stored data is unchanged.
- Passenger choice is Regular | Student · Senior · PWD, since both fare
  guides print one shared discounted column.
- Favicon replaced with the PadungGo header logo (SVG, 32px PNG, Apple
  touch icon).
- Panel headers restyled with a blue linocut style: navy to
  cobalt, printed speckles, a hand-cut white frame and a small star.

### Fare estimates (backend) — October 22, 2026

- Added per-ride PUJ guide estimates with integer-centavo arithmetic,
  per-ride kilometre ceiling, regular/discounted columns, and a 50 km
  limit. Vehicle classification remains unknown; verified fares and
  ranking remain unchanged. Added calculator, planner and API tests.

### Fare estimates in trip details (frontend) — October 22, 2026

- Passenger selector (Regular, Student, Senior, PWD) for the whole trip and a
  per-ride jeepney type picker (Traditional, Modern, Not sure).
- "Estimated total" summary and per-ride fare breakdown in the trip details
  panel; trip cards show the same total. "Not sure" shows the
  traditional-to-modern range; trip ranges add each ride's low and high.
- Amounts come from the backend's `guide_fare_estimate` (LTFRB PUJ guides,
  effective 2026-09-28). The frontend only picks and adds them. Verified
  fares keep priority and are never reused for another passenger type. Rides
  without a supported fare say "Ask the driver for this ride's fare." and no
  total is shown.
- Cream, moss and coral accents in the updated palette.
  Ride colours are now blue, moss, coral, charcoal, teal and plum.
- `formatFare` uses integer centavo maths and rejects fractional or negative
  amounts.

### Commuter UI redesign — October 21, 2026

- New blue design system with the updated visual direction: one blue accent,
  1px borders, 4px corners, a faint grid background, a self-hosted pixel
  display face (Pixelify Sans, OFL) and Lucide SVG icons. No emojis.
- Desktop/tablet: resizable left panel (drag, arrow keys, double-click to
  reset), collapsible, with width and state remembered. Phones: draggable
  bottom sheet over the map.
- Trips are named by boarding stop → final stop instead of "Option N", shown
  as expandable cards with a visual timeline (start, walk, board, get off,
  transfer, arrive) that uses the same colours as the map.
- Commuter-friendly wording: feed IDs, "historic route data" and similar
  technical text moved into (i) tooltips; waiting time omitted when unknown;
  unsupported fares read "Ask the driver". Approximate backend fares read
  "Estimated". No fare is calculated in the frontend.
- Map: custom zoom/fit controls, distinct start, board, transfer, exit and
  destination markers, route casing and fade-in, an "On map" trip chip, and
  compact OpenStreetMap/OpenMapTiles/OpenFreeMap credit in the map corner.
- API: journey `limit` maximum raised from 5 to 50. The app requests 50 and
  shows 8 at a time with "Show more", falling back to 5 on older deployments.
- Sort and transfer changes re-run the current search, and stale responses
  are ignored.
- Interface review follow-up:
  - Trip accordions replaced by a sliding, resizable "Trip details" panel
    beside the list (side by side on wide screens, over the list on tablets,
    full sheet view with "All trips" on phones).
  - Each ride has its own colour from the interface palette, used in
    the timeline, route plates, journey strip and map line.
  - Info tooltips, data-source notes and status text removed from commuter
    views; one short "Routes can change" note remains.
  - The Find trips button keeps its size and position while searching.
  - Map pins read "Pinned on map", not coordinates.

### Fare classification and display — October 22, 2026

- Review corrections: cheapest-label eligibility considers candidates before
  result truncation. Pricing requires verified pattern evidence in both strict
  and historical modes, without changing public source IDs or route visibility.
- Added regression tests for truncated fare comparisons and verified,
  documented-only and absent pattern evidence.

- Added backend fare classifications: exact, approximate and unavailable, with
  explanations. Supported flat fares can be exact; supported distance-band
  quotes remain approximate because recorded distance may differ from billable
  distance.
- Added distance-coverage checks and withheld quotes for unsupported partial
  distance bands and unresolved monetary rounding ties.
- Preserved verified-rule evidence, route-or-pattern scope, vehicle matching,
  mixed-fleet safeguards and passenger-category policies.
- Complete totals become approximate when any ride is approximate. An
  unavailable ride prevents a total price. Cheapest ranking and labels require
  complete exact fares for every candidate.
- Replaced unexplained fare Unknown text with an amount, an amount labelled
  Approximate, or Fare unavailable with an explanation.
- Documented additive API fields and the stricter quotation requirements.
- Local checks reported: 480 backend tests, 37 frontend tests and the frontend
  production build passed. These results do not establish production fare
  applicability or resolve the outstanding official-policy questions.
- No production data or verification statuses changed. Merge and deployment
  remain pending.

### Planner, search and journey display — October 20–21, 2026

Merged to `main`. Production deployment of #22 and #23 has not been verified yet.

**Planner**
- **Transfer stops (#23):** a transfer is offered only when both of its stops exist and have an allowed status. The stop where the first ride ends must allow getting off, and the stop where the second ride starts must allow boarding. Missing stop records no longer cause an error, and a blocked transfer point no longer hides a valid one between the same routes. This does not change which services count as currently operating.

**Fares**
- **Verified fare rules (#19):** a verified rule must name a route or pattern, match the route's vehicle class, rest on a verified pattern and have verified evidence. Rules for a whole vehicle class never price a journey. Mixed-fleet routes show the fare as Unknown, with the reason.
- **LTFRB fare guide (#20):** documented the LTFRB 2026-09-28 PUJ fare tables and added calculation regression tests. Recorded unresolved fractional-distance, discount-wording and vehicle-scope questions without changing production fares.

**Search and display**
- **Location search (#22):** case, accents, punctuation and extra spaces in a query are ignored, and every distinct word must match (at most six words). Only the query is normalised, not the stored names.
- **Journey steps (#21):** numbered walking, boarding, transfer and arrival steps, clearer same-stop transfers, walking-distance summaries, loading placeholders and reduced-motion support.
- **Server unavailable (#16):** when the API is starting up or unreachable (502/503/504), the app says so and asks you to try again, and marks the error as retryable.
- **Place search input (#15):** typed text is kept when a selected place is cleared, and outdated search requests are cancelled and their responses ignored.

**Data quality**
- **Placeholder route names (#17):** the importer drops feed placeholders such as "Name Missing".
- **17D/42D demo audit (#17, #18):** documented the demo journey, its geometry and its sources. Added a test that documented fare rules never produce a price. No production data was changed.

**Checks**
- 434 backend tests passed at the #23 head, which is identical to `main` at 47cd42a.
- On every pull request, CI runs the backend tests, a migration check, the frontend tests and the production build.

### Security and correctness fixes — October 19, 2026

**Security**
- **Production settings:** they no longer guess from the command line whether tests are running. Before, that guess could enable the dev secret key and skip the HTTPS/secure-cookie settings. Now the security settings depend only on `DJANGO_DEBUG`, and the server refuses to start in production with a missing or default development secret key. Tests use `config/test_settings.py`.
- **GTFS upload:**
  - Oversized uploads are refused from the `Content-Length` header (413) before Django reads the body.
  - The file must have a `.zip` extension and its contents must really be a zip archive.
  - Archives are rejected if they have too many files or would unzip to more than the size limit (zip-bomb guard).
- **`ensure_superuser`:** it no longer resets an existing admin's password on every restart. A deliberate reset needs `DJANGO_SUPERUSER_RESET_PASSWORD=True` or `--reset-password`.

**Correctness**
- **Stale journey results:** before, an import or admin edit refreshed only the one process that made it. Other workers, or every worker after `manage.py import_gtfs`, kept serving old journeys for up to 5 minutes. A shared `NetworkDataVersion` counter (migration `0003`) now makes every worker reload on its next request.
- **API behavior changes:**
  - `/locations` and `/routes` return 400 for an invalid `limit` or a malformed `area_id` or `cursor`.
  - `area_id` now filters `/routes`.
  - `cursor` pagination now works. Details are in docs/API_DESIGN.md.

**Tests**
- Added 33 regression tests covering the changes above.

**HSTS**
- Verified the live setup before enabling it: valid certificates on both hosts, HTTP redirects to HTTPS on both, and the API serves over TLS 1.3.
- The API now sends `Strict-Transport-Security: max-age=300`, a short starting duration that is configurable with `DJANGO_SECURE_HSTS_SECONDS`.
- `includeSubDomains` and `preload` stay disabled.

### Added
- Initial project concept, architecture, open-source contribution guidance and data-verification standards.

### Changed — October 17, 2026
- Distinguished full intra-city/intercity coverage vision, verified initial version subset and initial four-route research batch.
- Aligned the seven core documents, direction-aware schema, shared versioned API, independent returns and 3–5 distinct alternatives when available.
- Standardized unknown fare/time behavior and preserved detailed routing guidance.
- Visually reviewed all eight supplied mechanics images and recorded eligibility uncertainty, implementation gaps, audit and consistency review in docs/NEXT_STEPS.md.
- Updated supporting architecture, setup and data notes; no application code was added.

### Updated after participant clarification — October 17, 2026
- Recorded completed registration, intentionally private development repository, organizer permission to initialize after October 3, and October 23 at 11:59 PM submission deadline (Philippine time used for planning).
- Removed the resolved initialization-date blocker and retained public-release/submission and October 25 attendance tasks.
- Added a sourced, limited JeepMe/JTransit reference review; no competitor code or transport data imported.
- The earlier documentation ZIP remains a historical snapshot; repository documents contain these latest updates.

### Research update — October 17, 2026
- Documented a references-first approach with source and license checks for selective reuse.
- Reviewed CommuteTour and Cebu Jeepneys for 01K, 03Q, 20A and 23D; recorded source links, variant/alias questions, licensing, connectivity hypotheses and verification gaps.
- Flagged outdated fare references and the need for the applicable current LTFRB matrix; no routes, fares, coordinates, third-party code or map assets imported.

### Reference and planning update — October 17, 2026
- Added Suroy's guide as a secondary reference with metadata/fare-currency caveats; no operational data imported.
- Distinguished workshop tooling themes from explicit competition requirements and retained the checkpoint uncertainty.
- Added initial evidence, scope, and deployment planning priorities before implementation.

### Stack update — October 17, 2026
- Documented a proposed open-weight AI explanation layer and hosted inference interface; implementation came later.
- Kept the deterministic planner authoritative and Kiro/ACP/MCP as optional workshop/development context.

### Deployment clarification — October 17, 2026
- Recorded the project goal of a deployed application usable remotely.
- Described local inference as optional development tooling and planned a hosted inference path behind Django.
