# Demo journey audit: 17D → 42D (October 20, 2026)

This audit uses the desktop research in `docs/RESEARCH_17D_42D_2026-10-20.md` (online research only; nothing was observed in person). It does not change any record or status. The journey was reproduced with a read-only request to the production API; there was no direct database access.

## 1. The journey as the API returns it

The request below reproduces Option 1 (the origin is moved next to stop 2939, so the first walk is about 6 m instead of the demo's ~229 m):

```json
{"origin":{"latitude":10.32263,"longitude":123.89862},
 "destination":{"location_id":"51ce03c5-3e71-467b-a938-c46911558cfb"},
 "sort_by":"fewest_transfers","max_transfers":1,"limit":5}
```

| Leg | Record | Value from the API |
|---|---|---|
| Ride 1 | Route 17D | `dfae67a9-42e5-4e52-9f48-e9e536c71f59`, name `APAS - LAHUG - CARBON via Escario`, vehicle_class `jeepney`, operator `Department of Transportation, Cebu (DOTC)` |
| | Pattern | `704fc96e-2505-462c-9499-8b24ef20fbf8`, direction `unspecified`, signboard empty, status `documented` |
| | Board | occurrence `2d53ea54-8d30-4ad5-99f5-587e31ee28d6` (sequence 10), "Unnamed stop (feed id 2939)", 10.322633, 123.898678 |
| | Alight | occurrence `1beace6b-c925-4b7f-951e-fc5f6b26e8ae` (sequence 23), "Sanciangko", 10.296654, 123.893616 |
| | Distance / time | 4,055 m along the archived shape; 644 s from the archived schedule |
| Transfer | TransferConnection | from and to the **same** stop `b059f6e0-5b9a-4df7-a7e3-fcabe1b7121b` (Sanciangko), 0 m, no duration |
| Ride 2 | Route 42D | `52710e90-0b14-4c19-8f59-bf872927d2d4`, name `Name missing`, vehicle_class `jeepney`, same operator |
| | Pattern | `f7592fc3-21e4-41dd-9977-405cfb4040cc`, direction `unspecified`, signboard empty, status `documented` |
| | Board | occurrence `d7431581-ca0e-4b60-b400-4d613942978b` (sequence 43), Sanciangko (stop `b059f6e0…`) |
| | Alight | occurrence `327d5610-4691-4555-a3dc-226b5925b224` (sequence 72), "Cebu South Road", 10.28237, 123.857947 |
| | Distance / time | 4,443 m along the archived shape; 524 s from the archived schedule |
| Final walk | | 452.5 m in a straight line to the location "Cebu South Road & A Gabuya Street" (10.279336, 123.855191) |
| Source | DataSource | `929f1131-6577-4ced-95fa-0d3d55850b0b`, "Cebu DOTC GTFS (Transitland archive)", published date empty, **license empty** |
| Fare rules | | None applied (`rule_id: null` on both legs) |

The API doesn't return the database IDs of stop 2939 or the Cebu South Road stop. You can find them with the query in section 6.

## 2. Why each "Unknown" or warning appears

| What you see | Cause | What would change it |
|---|---|---|
| Fare: Unknown on both legs | The planner loads only `FareRule` rows with status `verified` (`planner/loader.py`), and the API reports no applicable rule. The production fare table may simply be empty; the section 6 query will confirm. | A verified rule for the right vehicle class, once the blockers in section 4 are resolved |
| Total fare incomplete | Follows from the unknown leg fares | Same |
| Riding 19 min (schedule) | Known: 644 + 524 s from the archived timetable. Historic, not observed | — |
| Waiting: Unknown | The planner has no frequency data and always reports waiting as unknown (`planner/assembly.py`) | Needs new data **and** a code change, so it can wait until after the demo |
| Walking: Unknown | Access and exit walks are straight lines by design | A walking-path feature (after the demo) |
| "Unnamed stop (feed id 2939)" | The archived feed had no name for this stop, and the importer shows this honest fallback | A name checked in person (worksheet) |
| "Name Missing" on 42D | The feed's route name is the placeholder text `Name missing`. The importer filtered placeholders out of stop names but not route names, and the frontend capitalises it. | Fixed for future imports on `fix/route-name-placeholder`; the existing record needs the Admin edit in section 3 |
| "Transfer: walk from Sanciangko to Sanciangko" | Both patterns share one archived stop record, so the transfer is 0 m at the same point | An in-person check that the 17D drop-off and 42D pickup really are the same spot |
| Historic data · not field-verified | Both patterns are `documented`, and production allows documented data (`PLANNER_ALLOW_DOCUMENTED=True`) | Keep it. The research supports labels, not verification |
| Exit stop "Cebu South Road" | The stop is 452.5 m from the A. Gabuya junction, so it is **not** at the junction | — |

## 3. Admin entry plan

Nothing here changes a pattern, stop, transfer or verification status. Every edit of a routable record clears the network cache automatically (`transit/signals.py`).

### 3a. DataSource records (Admin → Data sources → Add)

`collected_at` is required and holds the **online check** date (2026-10-20), not an in-person observation. `DataSource` has no reviewer field, so the reviewer goes on the evidence rows in 3c. Write "Unknown — not established" in `license` rather than leaving it blank, so it can't be mistaken for an oversight.

| # | title | publisher | reference | published_at | limitations (scope of what it supports) |
|---|---|---|---|---|---|
| S1 | Palace: Gov't balances transport support, commuter welfare amid fare hike and rising fuel prices | Presidential Communications Office | pco.gov.ph URL from the research | 2026-09-28 | Confirms ₱14 (traditional) and ₱17 (modern) minimums and that concession discounts continue. No per-km matrix, rounding, Cebu route fleets or end date. |
| S2 | LTFRB sets new PUV rates effective Sept. 28 | SunStar / Philippine News Agency | sunstar URL | 2026-09-29 | Reports the effective date, first-4-km coverage, and ₱2.00 / ₱2.40 per succeeding km. A news report, not the LTFRB matrix. |
| S3 | DOTr approves LTFRB fare hike recommendation for PUVs | GMA News | gmanetwork URL | 2026-09-25 | Corroborates the same rates. Only search-index text was seen; the article itself failed to load on 2026-10-20. |
| S4 | Labella issues EO allowing Talisay, Mandaue TPUJs in Cebu City | The Freeman (Philstar) | philstar URL | 2021-03-14 | Historical authorization (EO 122, 2021) of 42D Poblacion Talisay–Cebu City via V. Rama–Taboan, traditional jeepneys. Does not prove current operation, path or fleet. |
| S5 | What Mandaue City or Talisay City jeepneys can enter Cebu City? | CDN Digital | cebudailynews URL | 2021-03-12 | Corroborates S4 (search-index text). Same limits. |
| S6 | 17D route page | Cebu Jeepneys (independent directory) | weebly URL | *(leave blank: undated)* | Directory lead for 17D Apas–Carbon via Taboan and landmarks. Undated; the page carries an inconsistent 04L label. Not authoritative routing. |
| S7 | Apas routes | CommuteTour | commutetour URL | *(leave blank)* | Page shows a 2026-01-19 update, but its fare section is from October 2023, so the update date does not cover every claim. Directory lead only. |

All rows: `collected_at` = 2026-10-20 (Asia/Manila; time not recorded), and `license` = "Unknown — not established".

Leave out the Cebu Bus Spotters page and the Reddit posts. They mix active and inactive routes or are unattributed, and they add nothing the rows above don't.

### 3b. Route names (Admin → Routes)

| Record | Field | Current | Proposed now | Why | Before using the research label |
|---|---|---|---|---|---|
| 42D `52710e90…` | `name` | `Name missing` | *(blank)* | Removes a placeholder that looks like a real name. When the name is empty the frontend shows just "Ride 42D". | Open the 42D pattern `f7592fc3…` in Admin and check that its stop list follows V. Rama and Taboan. Only then set **"Poblacion Talisay – Cebu City via V. Rama and Taboan"** (S4/S5). Otherwise the label would describe a path the map doesn't show. |
| 17D `dfae67a9…` | `name` | `APAS - LAHUG - CARBON via Escario` | **No change** | This name comes from the same archived feed as the geometry on the map. The directory label "via Lahug, Capitol and Taboan" (S6/S7) describes the corridor differently and isn't more authoritative. | An official route description |
| Both | `vehicle_class` | `jeepney` | **No change** | This is the importer's default (`gtfs_types.py`), not evidence. The research doesn't establish either fleet. | Official fleet or operator confirmation |
| Both | `operator` | DOTC (the feed agency) | **No change** | No operator or cooperative was established | Operator or LTFRB record |

There is no source field on `Route`, so a name change can only be justified with a `RouteEvidence` row (3c).

### 3c. Evidence rows (append-only)

| Model | Target | source | status | reviewed_at / reviewer | observed_at | notes |
|---|---|---|---|---|---|---|
| RouteEvidence | pattern `f7592fc3…` (42D) | S4 | **candidate** | 2026-10-20 / *your name* | blank | "Supports the route display name only. Does not verify current operation, geometry, stops or fleet." |
| RecordEvidence | each FareRule from 3d | S1, and S3 on a separate row | **documented** | 2026-10-20 / *your name* | blank | State what each source supports (S1: minimums only; S3: corroboration only) |

Why `candidate` for the route row: the loader includes `documented` RouteEvidence as a pattern source in production (`_load_pattern_evidence`). A documented news citation would then appear under "Source:" as if it supported the archived geometry. A `candidate` row keeps the provenance without that.

### 3d. Fare rules: record for review, don't activate (Admin → Fare rules → Add)

| Field | Traditional | Modern |
|---|---|---|
| vehicle_class | `jeepney` | `modern_puv` |
| route / pattern | blank | blank |
| passenger_category | `regular` | `regular` |
| kind | `distance_band` | `distance_band` |
| policy | `{"base_centavos":1400,"base_distance_m":4000,"increment_centavos":200,"increment_distance_m":1000}` | `{"base_centavos":1700,"base_distance_m":4000,"increment_centavos":240,"increment_distance_m":1000}` |
| valid_from / valid_until | 2026-09-28 / blank | 2026-09-28 / blank |
| status | **documented** (the planner ignores it) | **documented** |
| source | S2 (the only source that states the full base-plus-increment policy) | S2 |

`rounding_centavos` is left out on purpose because it is unconfirmed. Do not create a flat ₱14 or ₱17 rule, and do not create student, senior or PWD rules yet.

## 4. Fare readiness

**Confirmed:** the base fares, the 4 km base distance, the per-km increments and the 2026-09-28 effective date. The schema can store all of these.

**Unconfirmed, and each one changes the demo fare:**

1. **Part kilometres.** The code charges a full increment for any part of a kilometre (`math.ceil`). On the demo legs:

   | Leg | Distance | Charging any part of a km (current code) | Nearest whole km | Whole km, rounded down |
   |---|---|---|---|---|
   | 17D | 4,055 m | ₱16.00 trad. / ₱19.40 modern | ₱14.00 / ₱17.00 | ₱14.00 / ₱17.00 |
   | 42D | 4,443 m | ₱16.00 / ₱19.40 | ₱14.00 / ₱17.00 | ₱14.00 / ₱17.00 |

   If the official matrix uses whole-km rounding instead of charging part kilometres, `compute_leg_fare_centavos` needs a new policy key, for example `distance_rounding: "ceil" | "nearest" | "floor"`, plus tests.
2. **Rounding money.** The code can only round to the *nearest* step, using Python's `round()`. With these rates and a 25-centavo step a tie can't happen, so that's safe. If the matrix rounds **up or down** instead, a `rounding_mode` key is needed.
3. **Discount amounts.** These would need separate per-category rules, and the planner always asks for `regular` (`planner/engine.py`); the API has no passenger-type input. This is a code change, so it can wait until after the demo.
4. **Vehicle class.**
   - `VehicleClass` offers only `jeepney`, `modern_puv` and `bus`. If the 2026 matrix splits modern jeepneys into classes (for example air-conditioned versus not), the enum needs a migration.
   - `vehicle_class` is stored on `Route`, so one route code has exactly one class. A route that runs a mixed fleet can't be represented. Showing both fares on a mixed-fleet leg would also need a code change.
5. **Scope of a class-wide rule.** A verified `jeepney` rule with route and pattern left blank would price **every** imported route, because the importer gave them all `jeepney` by default. That includes 17D, whose fleet is unconfirmed. Route-specific rules avoid this, but they need confirmed fleets. **This is your decision** before anything is set to verified.
6. **Distances.** Fares would use the archived shape distances, which are documented, not verified.

**Verdict:** Admin entry alone is enough only if the official matrix charges part kilometres the way the current code does and rounds to the nearest step, and only once each route's fleet is confirmed. Otherwise the code changes above come first.

## 5. Field-verification worksheet

Prefilled values come from the archived feed through the API. The direction is *inferred* from the archived stop order and is unconfirmed.

**Visit:** date ____ time (Asia/Manila) ____ reviewer ____ weather / traffic ____

| | Point 1: board 17D | Point 2: get off 17D | Point 3: board 42D | Point 4: get off 42D |
|---|---|---|---|---|
| Archived name | Unnamed stop (feed id 2939) | Sanciangko | Sanciangko (same stop record) | Cebu South Road |
| Archived coordinates | 10.322633, 123.898678 | 10.296654, 123.893616 | 10.296654, 123.893616 | 10.28237, 123.857947 |
| Pattern / occurrence | 704fc96e… / 2d53ea54… (seq 10) | 704fc96e… / 1beace6b… (seq 23) | f7592fc3… / d7431581… (seq 43) | f7592fc3… / 327d5610… (seq 72) |
| Inferred direction | toward Carbon | toward Carbon | toward Talisay | toward Talisay |
| Name locals use | | | | |
| Nearest corner or landmark | | | | |
| Street and street side | | | | |
| Measured coordinates (from your phone) | | | | |
| Do jeepneys actually stop here? (yes / no / only informally) | | | | |
| Signs or rules against loading here | | | | |
| Safe place to stand / sidewalk | | | | |
| Front sign seen (exact text) | | | | |
| Vehicle type (traditional / modern / both) | | | | |
| Units seen in 15 min, and the times | | | | |
| Photo taken (no faces or plates) | | | | |
| Notes | | | | |

**Transfer walk (Point 2 → Point 3):** Are they the same spot? ____ If not: walking distance ____ m, time ____ min, street crossings ____, barriers or one-way issues ____, lighting or safety ____, notes ____

**Point 4 → destination (Cebu South Road & A. Gabuya, 10.279336, 123.855191):** real walking distance ____ m, crossing ____, notes ____

## 6. Read-only database check (Supabase → SQL Editor)

Run this before renaming anything. It lists every route that uses the stops above, so a shared stop name isn't changed blindly. It only reads (`SELECT`).

```sql
SELECT s.id AS stop_id, s.name, s.latitude, s.longitude, s.status,
       r.code, p.id AS pattern_id, p.direction, ps.sequence
FROM transit_stop s
JOIN transit_patternstop ps ON ps.stop_id = s.id
JOIN transit_routepattern p ON p.id = ps.pattern_id
JOIN transit_route r ON r.id = p.route_id
WHERE s.id = 'b059f6e0-5b9a-4df7-a7e3-fcabe1b7121b'
   OR s.name IN ('Unnamed stop (feed id 2939)', 'Cebu South Road')
ORDER BY s.name, r.code, ps.sequence;

SELECT id, vehicle_class, passenger_category, kind, status, valid_from FROM transit_farerule;
```
