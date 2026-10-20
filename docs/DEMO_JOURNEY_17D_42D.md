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

Stop IDs, from the read-only Supabase query the owner ran on 2026-10-20:

| Stop | Stop ID | Other patterns using the same record |
|---|---|---|
| Unnamed stop (feed id 2939) | `7c12b541-1651-409f-bd0c-6da304b0ad50` | 11 patterns: 03D, 04C, 04D, 04E, 04I, 04L, 17B, 17C, 17D, 51E, 60 |
| Sanciangko (transfer) | `b059f6e0-5b9a-4df7-a7e3-fcabe1b7121b` | 30 patterns, including 17C, 17D, 42D, 43, 51E, 64C and the 02/04/09/10/12/13 series |
| Cebu South Road (42D exit) | `22d44f9b-5da3-4684-a28a-f7e0c4e6f80c` | 10C, 10E, 10J, 10K, 10M, 10O, 41D, 42D (twice: seq 8 and 72), 43 |

Renaming any of these records changes the name for every pattern listed.

## 2. Why each "Unknown" or warning appears

| What you see | Cause | What would change it |
|---|---|---|
| Fare: Unknown on both legs | The planner loads only `FareRule` rows with status `verified` (`planner/loader.py`), and the API reports no applicable rule for `jeepney`/`regular` today. A regression test (`test_plan_ignores_documented_fare_rules`) guarantees that documented rules are never priced. | A verified rule for a confirmed fleet, once the blockers in section 4 are resolved |
| Total fare incomplete | Follows from the unknown leg fares | Same |
| Riding 19 min (schedule) | Known: 644 + 524 s from the archived timetable. Historic, not observed | — |
| Waiting: Unknown | The planner has no frequency data and always reports waiting as unknown (`planner/assembly.py`) | Needs new data **and** a code change, so it can wait until after the demo |
| Walking: Unknown | Access and exit walks are straight lines by design | A walking-path feature (after the demo) |
| "Unnamed stop (feed id 2939)" | The archived feed had no name for this stop, and the importer shows this honest fallback | A name checked in person (worksheet) |
| "Name Missing" on 42D | The feed's route name is the placeholder text `Name missing`. The importer filtered placeholders out of stop names but not route names, and the frontend capitalises it. | Fixed for future imports by PR #17 (merged). The existing record still needs the Admin edit in 3b; the fix doesn't rewrite stored data. |
| "Transfer: walk from Sanciangko to Sanciangko" | The importer creates a 0 m "same-stop reboarding" transfer at every stop served by more than one route (`_derive_same_stop_transfers` in `importers/gtfs.py`, labelled "not a field-verified interchange"). See section 7. | An in-person check that the 17D drop-off and 42D pickup really are the same spot |
| Historic data · not field-verified | Both patterns are `documented`, and production allows documented data (`PLANNER_ALLOW_DOCUMENTED=True`) | Keep it. The research supports labels, not verification |
| Exit stop "Cebu South Road" | The stop is 451 m from the A. Gabuya junction, so it is **not** at the junction. It is the last 42D stop in the archive's Talisay-bound direction (section 7). | An in-person check of where Talisay-bound 42D units stop near A. Gabuya |

## 3. Admin entry plan

Nothing here changes a pattern, stop, transfer or verification status. Every edit of a routable record clears the network cache automatically (`transit/signals.py`).

### 3a. DataSource records (Admin → Data sources → Add)

`collected_at` is required and holds the **online check** date (2026-10-20), not an in-person observation. `DataSource` has no reviewer field, so the reviewer goes on the evidence rows in 3c. Write "Unknown — not established" in `license` rather than leaving it blank, so it can't be mistaken for an oversight.

*Revised 2026-10-20 after the second research pass.* Only sources that a record below actually cites are entered. The numbers in brackets refer to the source register in `docs/RESEARCH_17D_42D_2026-10-20.md`.

| # | title | publisher | reference | published_at | limitations (scope of what it supports) |
|---|---|---|---|---|---|
| S1 | LTFRB releases new matrices for PUV fare hikes effective Sept. 28 [11] | PTV News | ptvnews.ph URL | *(blank: not shown on the page)* | Regular and discounted PUJ rates (traditional ₱14 / ₱2.00, discounted ₱11.25 / ₱1.60; modern ₱17 / ₱2.40, discounted ₱13.50 / ₱1.92), effective 2026-09-28. A news summary of the LTFRB guides. Gives no rule for part kilometres or rounding, and no modern sub-classes. |
| S2 | Usbaw nga P1 ug P2 sa pletihan gipatuman na [12] | Banat (Philstar), Joy Torrejos | philstar.com/banat URL | 2026-09-29 | Cebu applicability: ₱14 / ₱17 minimums in effect from 2026-09-28. The LTFRB says a temporary fare guide is in use. No distance table. |
| S3 | Palace: Gov't balances transport support, commuter welfare amid fare hike and rising fuel prices [1] | Presidential Communications Office | pco.gov.ph URL | 2026-09-28 | Government confirmation of the minimums and that discounts continue. No per-km rates. |
| S4 | Cebu BRT Social Management Plan, Vol. 1, Tables 1 and 3 [13] | World Bank (hosted) | documents1.worldbank.org URL | 2021-06-10 (PDF creation date) | 42D "Talisay via N. Bacalso, V. Rama Taboan v.v."; 17D "Apas to Taboan via Osmeña Boulevard". From LTFRB franchise data that includes non-operating franchises, so subject to validation. Historical only. |
| S5 | Labella issues EO allowing Talisay, Mandaue TPUJs in Cebu City [4] | The Freeman (Philstar) | philstar URL | 2021-03-14 | Historical authorization (EO 122, 2021) of 42D for traditional jeepneys. Doesn't prove current operation, path or fleet. |

All rows: `collected_at` = 2026-10-20 (Asia/Manila; time not recorded), and `license` = "Unknown — not established".

**Changes from the first plan:**
- **Dropped:** SunStar and GMA (superseded by the government-owned PTV and the Cebu-specific Banat report), CDN Digital (duplicates S5), the Cebu Jeepneys and CommuteTour directories (the 17D name isn't changing, so no record cites them), and PNA (the article returned 404 and couldn't be checked). They all stay in the research register.
- **Kept out, as before:** the community directories and Reddit posts.

### 3b. Route names (Admin → Routes)

| Record | Field | Current | Proposed now | Why | Before using the research label |
|---|---|---|---|---|---|
| 42D `52710e90…` | `name` | `Name missing` | *(blank)*, so the app shows "Ride 42D" | Removes the placeholder. **Decided after the geometry check (section 7):** keep the name neutral. The archived pattern starts in Bulacao (Cebu City), never reaches Poblacion Talisay, and only touches V. Rama Avenue. "Poblacion Talisay – Cebu City via V. Rama and Taboan" (S4/S5) would describe a path the map doesn't show. | Current geometry that reaches Talisay, or an official description matching the archived path |
| 17D `dfae67a9…` | `name` | `APAS - LAHUG - CARBON via Escario` | **No change** | The demo leg follows N. Escario Street and Osmeña Boulevard. That matches this feed name and also S4 ("via Osmeña Boulevard"), so the name doesn't conflict with the evidence. S4 ends 17D at Taboan, not Carbon, and the archived pattern beyond Sanciangko wasn't checked. | An official current route description |
| Both | `vehicle_class` | `jeepney` | **No change** | This is the importer's default (`gtfs_types.py`), not evidence. The research doesn't establish either fleet. | Official fleet or operator confirmation |
| Both | `operator` | DOTC (the feed agency) | **No change** | No operator or cooperative was established | Operator or LTFRB record |

There is no source field on `Route`, so a name change can only be justified with a `RouteEvidence` row (3c).

### 3c. Evidence rows (append-only)

| Model | Target | source | status | reviewed_at / reviewer | observed_at | notes |
|---|---|---|---|---|---|---|
| RouteEvidence | pattern `f7592fc3…` (42D) | S4 | **candidate** | 2026-10-20 / *your name* | blank | "Historical franchise listing: Talisay via N. Bacalso, V. Rama, Taboan. The archived pattern matches N. Bacalso and Tres de Abril (Taboan), only touches V. Rama, and starts in Bulacao, not Talisay. Not current operation; no stops or fleet verified." |
| RouteEvidence | pattern `704fc96e…` (17D) | S4 | **candidate** | same | blank | "Historical franchise listing: Apas to Taboan via Osmeña Boulevard. The demo leg follows N. Escario St and Osmeña Blvd. Not current operation." |
| RecordEvidence | each FareRule from 3d | S2 (Cebu applicability) and S3 (government confirmation), one row each | **documented** | same | blank | State what each source supports, as in the 3a limitations column |

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
| source | S1 (PTV, which states base plus increment) | S1 |

- **`rounding_centavos`** is left out on purpose because the 2026 rule is unconfirmed.
- **No flat rule:** don't create a flat ₱14 or ₱17 rule.
- **No discount rules yet:** the discounted amounts are confirmed (S1), but each needs three rules (student, senior, PWD) per vehicle class, and the planner can't use them yet (section 4, item 3). They're recorded in the research doc.
- **Older rules:** don't create new ₱13 or ₱15 rules, because their per-km amounts weren't sourced. If the fare table already holds older rules, keep them (don't delete). Give any that lack an end date `valid_until` = 2026-09-27, so they can't overlap the new rates. The second query in section 6 shows whether any exist.
- **Activation:** these two rules stay `documented`. When the temporary fare guide is in hand, follow the activation rule: create **route-scoped** verified rules only for routes whose fleet is confirmed. Never use a class-wide verified rule, which would price every route labelled `jeepney`.

## 4. Fare readiness

**PDF review, 2026-10-21:** both supplied LTFRB guides have been read.
Each is one page and states an effective date of 2026-09-28.
See [the complete transcription and audit](FARE_GUIDE_2026-09-28.md)
for source URLs, download date, old/new tables and limitations.

**What the guides settle:**
- Traditional: P14.00 for the first 4 km, then P2.00/km.
- Aircon modern and electric PUJ: P17.00 for the first 4 km, then P2.40/km.
- Discounted computation uses P11.20 plus P1.60/km for traditional,
  and P13.60 plus P1.92/km for aircon modern/electric.
- Round the calculated amount to the nearest P0.25. The rounded discounted
  minimums are P11.25 and P13.50; those are not the computation bases.
- At exactly 5 km, the modern table prints P19.50 regular and P15.50
  discounted, not P19.40 regular.
- All 200 new-fare cells match the current calculator with the policy
  inputs below. No calculator, validator or schema change is needed.
  The PR must separately record the owner's test results.

### Proposed policy JSON for later documented rules

These are review inputs, not instructions to write production data.
All four use kind `distance_band`, currency `PHP`, status `documented`,
and valid_from `2026-09-28`. Neither supplied page prints an expiry date;
any valid_until decision remains subject to source review.

Traditional regular:

```json
{
  "base_centavos": 1400,
  "base_distance_m": 4000,
  "increment_centavos": 200,
  "increment_distance_m": 1000,
  "rounding_centavos": 25
}
```

Traditional student / elderly / PWD:

```json
{
  "base_centavos": 1120,
  "base_distance_m": 4000,
  "increment_centavos": 160,
  "increment_distance_m": 1000,
  "rounding_centavos": 25
}
```

Aircon modern/electric regular:

```json
{
  "base_centavos": 1700,
  "base_distance_m": 4000,
  "increment_centavos": 240,
  "increment_distance_m": 1000,
  "rounding_centavos": 25
}
```

Aircon modern/electric student / elderly / PWD:

```json
{
  "base_centavos": 1360,
  "base_distance_m": 4000,
  "increment_centavos": 192,
  "increment_distance_m": 1000,
  "rounding_centavos": 25
}
```

A discounted JSON is shared across the three published discount categories;
it is not a new combined passenger-category enum value. Any later category
records require separate review. The planner currently requests regular
fares, and this work does not change that behavior.

The modern JSON documents only the named aircon modern/electric guide.
Do not apply it to all `modern_puv` routes without subtype evidence.
No vehicle classes are added by this work.

### What remains unresolved

1. **Fractional kilometres: not stated.** Neither PDF establishes ceil,
   nearest or floor. Traditional 4.055 km therefore remains officially
   unresolved. The existing calculator returns P16.00; that is preserved
   behavior, not an official determination. The same uncertainty affects
   the 4.443 km demo leg. Boundary tests at 4,001 m preserve this behavior.
2. **Discount wording:** both PDFs say students receive a discount of
   "not less than 20%" while some rounded table amounts exceed 80% of
   the rounded regular fare. For example, traditional P14.00/P11.25 and
   modern 6 km P21.75/P17.50. The tables match the printed add-on formulas
   and rounding, but LTFRB-7 should clarify the wording before activation.
   Do not silently change the published discounted values.
3. **Fleet and subtype:** the modern guide explicitly names aircon modern
   and electric PUJs; it supplies no separate non-aircon modern rate.
   Confirm applicability for the actual fleet. Imported `jeepney` labels
   alone are not fleet evidence. Conflicting 42D fleet sources remain open.
4. **Mixed routes:** the existing `mixed` class keeps fares Unknown.
   This work does not add subtype modelling or multiple fare options.
5. **Distances and route verification:** archived distances and the
   documented demo patterns are not made verified by a fare-table test.
6. **Source and applicability review:** confirm the supplied Drive-link
   mapping, applicable geographic coverage and evidence records before
   production entry. Complete the section 8 read-only pre-check first.

**Precedence for later review:** this section replaces section 3d's older
proposal to omit rounding. Sections 3 and 8 are historical prepared plans,
not authorization to execute writes in this task. Their proposed evidence
and policies must be reconciled with the PDFs before any later Admin work.

**Verdict:** integer-distance fare arithmetic is supported by the guides;
demo fares remain Unknown until the outstanding applicability, distance
and verification requirements are resolved. Route/pattern scoping,
fleet matching, verified evidence and all existing safeguards stay intact.

No Supabase/Admin writes, seeds, migrations, production verification
changes or deployment are included. Synthetic verified policies exist
only inside the pure-Python tests. The owner keeps the PR unmerged and
decides when to merge and deploy.

## 5. Field-verification worksheet

Prefilled values come from the archived feed through the API. The direction is *inferred* from the archived stop order and is unconfirmed.

**Visit:** date ____ time (Asia/Manila) ____ reviewer ____ weather / traffic ____

| | Point 1: board 17D | Point 2: get off 17D | Point 3: board 42D | Point 4: get off 42D |
|---|---|---|---|---|
| Archived name | Unnamed stop (feed id 2939) | Sanciangko | Sanciangko (same stop record) | Cebu South Road |
| Archived coordinates | 10.322633, 123.898678 | 10.296654, 123.893616 | 10.296654, 123.893616 | 10.28237, 123.857947 |
| Stop ID | 7c12b541… | b059f6e0… | b059f6e0… | 22d44f9b… |
| Pattern / occurrence | 704fc96e… / 2d53ea54… (seq 10) | 704fc96e… / 1beace6b… (seq 23) | f7592fc3… / d7431581… (seq 43) | f7592fc3… / 327d5610… (seq 72) |
| Street per OSM (not a stop name) | Gorordo Avenue | Sanciangko Street | Sanciangko Street | Natalio Bacalso Avenue, Poblacion Pardo |
| Inferred direction and heading | toward downtown, via N. Escario | westbound (≈254°) | westbound (≈250°) | toward Talisay (south-west) |
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

The archive uses **one stop record for both directions** at many points: 42D passes stop 22d44f9b at seq 8 and seq 72, and 971c98da at seq 24 and 58. So "street side" can't be taken from the data. Record it for each direction you check.

**Transfer walk (Point 2 → Point 3):** Are they the same spot? ____ If not: walking distance ____ m, time ____ min, street crossings ____, barriers or one-way issues ____, lighting or safety ____, notes ____

**Point 4 → destination (Cebu South Road & A. Gabuya, 10.279336, 123.855191):** real walking distance ____ m, crossing ____, notes ____

## 6. Read-only database checks (Supabase → SQL Editor)

The owner ran the first query on 2026-10-20 (366 rows; results summarised in sections 1 and 7). The fare-table check has been replaced by the combined pre-check in section 8. Every query here only reads (`SELECT`).

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

Optional: run this only if you want 42D's full stop list. Section 7 doesn't need it.

```sql
SELECT ps.sequence, s.id, s.name, s.latitude, s.longitude
FROM transit_patternstop ps JOIN transit_stop s ON s.id = ps.stop_id
WHERE ps.pattern_id = 'f7592fc3-21e4-41dd-9977-405cfb4040cc'
ORDER BY ps.sequence;
```

## 7. Pattern and geometry check (2026-10-20)

**Method:** Kiro took the archived ride geometry the production API returns for the 17D demo leg and for 42D (seq 0 → 44 and seq 43 → 72). It then looked up the street names along it in OpenStreetMap (reverse geocoding through Nominatim; data © OpenStreetMap contributors, ODbL). The OSM names are used only to check alignment. They are **not** proposed as stop names.

### 42D against the historical description ("Talisay via N. Bacalso, V. Rama, Taboan v.v.", S4)

| Part of the description | Archived pattern `f7592fc3…` | Match? |
|---|---|---|
| N. Bacalso Avenue | Followed from Bulacao through Pardo, Basak and Mambaling (including the flyover and underpass), in both directions | Yes |
| Taboan | The downtown loop runs Panganiban → Colon → J. Climaco → Sanciangko → Tres de Abril → B. Aranas Extension. Tres de Abril passes about 120 m from Tabo-an Public Market. | Consistent |
| V. Rama Avenue | The geometry comes within 3–4 m of V. Rama only at its southern end, near N. Bacalso, for about 20 m in each direction. It does **not** run along the avenue. | Only touches it |
| Talisay endpoint | Seq 0 is at 10.27253, 123.848253, in **Bulacao, Cebu City**. The pattern never reaches Poblacion Talisay. | **No** |
| Return trip | The Talisay-bound part ends at seq 72 (stop 22d44f9b, Poblacion Pardo), about 1.2 km before seq 0. The loop isn't closed. | Incomplete |

**Conclusion:** the pattern is *consistent with part of* the documented corridor, but it is truncated at both ends. Keep 42D's name neutral (3b) and keep the `documented` status. Don't move stops, extend the geometry or invent the Talisay section.

### 17D demo leg (seq 10 → 23)

Gorordo Avenue (stop 2939) → N. Escario Street → Osmeña Boulevard → Fuente Osmeña Circle → Osmeña Boulevard → Sanciangko Street. This fits the feed name ("via Escario") and S4 ("via Osmeña Boulevard"). Directory labels "via Lahug, Capitol" (research sources 6 and 7) also fit this corridor, since Escario runs past the Capitol. Nothing conflicts, so the name stays.

### The Sanciangko transfer

- **Where it comes from:** the importer created a 0 m "same-stop reboarding" transfer at stop b059f6e0, because 30 patterns use it. The record says "not a field-verified interchange".
- **Direction:** 17D arrives heading about 254° and 42D leaves heading about 250°. Both are westbound on Sanciangko Street at the same point, which fits reboarding on the same side of the street.
- **Not established:** whether jeepneys may load there, whether the street is one-way, and where they actually stop. These need the site visit.

### The exit stop, 451 m from the destination

- **Why that stop:** stop 22d44f9b is the last stop in the archive's Talisay-bound direction. The closer stop 083ce96a (163 m from the A. Gabuya junction) appears only in the city-bound direction (seq 7), so the planner correctly doesn't use it for this trip.
- **What to check on site:** where Talisay-bound 42D units really stop near A. Gabuya.

### "Cebu South Road" names (22 distinct stop records in the export)

- **On N. Bacalso:** OSM puts 16 of these records on Natalio Bacalso Avenue, so for those the generic name is consistent.
- **Probably on N. Bacalso:** 083ce96a (10.280419, 123.856207; used by 10C, 10E, 10M, 10O, 41D, 42D, 43) resolves to I. Tabura Street. It's probably at a side-street junction with N. Bacalso, but that needs checking.
- **On other streets:** OSM places 5 records elsewhere, so their name is suspect:

  | Stop | Coordinates | OSM street | Used by |
  |---|---|---|---|
  | e5f22074 | 10.30942, 123.876066 | Ramon Duterte St, Labangon | 07A–07D, 12K, 12L |
  | 5c3603c7 | 10.294321, 123.870091 | E. Sabellano St, Punta Princesa | 09J, 09K, 10J, 12A–12N |
  | db5b0c41 | 10.297364, 123.877595 | Tres de Abril St, Punta Princesa | 12A–12M |
  | b06eac57 | 10.288147, 123.857934 | E. Sabellano St, Quiot Pardo | 10J |
  | 1e5df3cc | 10.278662, 123.863157 | L. Gabuya St, Cogon Pardo | 11A, 11D |

- **Not touched:** none of these five are on the demo journey. Renaming them would change the name for the routes listed, so they're left for review. Possible approaches are a status of `needs_review` or a site check; it is not urgent for the demo.
- **One record for both directions:** many of these records serve both directions (section 5), so a single name can't describe the street side.

## 8. Fare safeguard and prepared production changes (2026-10-20)

### What the safeguard enforces

| Layer | Rule | Where |
|---|---|---|
| Admin save | A rule can be set to **verified** only if: it names a route or pattern; its vehicle class equals that route's; the fleet is confirmed (the pattern, or at least one pattern of the route, is `verified`, because vehicle type is check 1 of `DATA_VERIFICATION.md`); and a **verified** `RecordEvidence` row points at the rule. Each failure shows its own message. | `FareRule.clean` in `models/fares.py` |
| Admin save | A rule can never be for `mixed`. | same |
| Planner | Class-wide rules (no route or pattern) never price a leg. The vehicle class must still match, so reclassifying a route stops the old rule from applying. | `planner/fares.py` |
| Loader | A rule whose status is verified but which has no verified evidence is not loaded. This covers changes made outside Admin. | `planner/loader.py` |
| Mixed fleet | A new vehicle class, `mixed` ("Mixed fleet (traditional and modern)"). A mixed route's fare stays Unknown, with the reason "This route runs both traditional and modern vehicles; the fare depends on the vehicle you board." | `models/enums.py`, migration `0004` (a choices change only; the database operation is a no-op), `planner/assembly.py` |

**Consequence for the demo:** 17D and 42D have only `documented` patterns. Admin will refuse a verified fare for them until one of their patterns is verified. So "Fare: Unknown" stays on the demo until both the official guide and a verified pattern exist. That is intended.

**Possible effect on production:** production has no verified rule that applies today (both demo legs return `rule_id: null`). If the check below finds a verified rule that is class-wide or lacks evidence, it will stop applying once this change is deployed. Its fare then shows Unknown; no incorrect price is shown.

### Prepared change set (not executed)

**Step 0: read-only pre-check.**
- **Where to run it:** Supabase → project → SQL Editor → New query. Paste the query and Run, then copy the results.
- **What it checks:** existing fare rules and their dates, possible duplicate sources, the current 17D/42D route and pattern rows, and existing evidence.

```sql
SELECT 'fare_rule' AS item, f.id::text AS id,
       concat_ws(' | ', f.vehicle_class, f.passenger_category, f.kind, f.status,
                 'route=' || coalesce(r.code, '-'), 'pattern=' || coalesce(f.pattern_id::text, '-'),
                 'from=' || f.valid_from::text, 'until=' || coalesce(f.valid_until::text, 'open'),
                 f.policy::text) AS detail
FROM transit_farerule f LEFT JOIN transit_route r ON r.id = f.route_id
UNION ALL
SELECT 'fare_evidence', e.id::text, concat_ws(' | ', e.fare_rule_id::text, e.status, s.title)
FROM transit_recordevidence e JOIN transit_datasource s ON s.id = e.source_id
WHERE e.fare_rule_id IS NOT NULL
UNION ALL
SELECT 'possible_duplicate_source', s.id::text, concat_ws(' | ', s.title, s.reference)
FROM transit_datasource s
WHERE s.reference ILIKE ANY (ARRAY['%ptvnews.ph%', '%philstar.com/banat%', '%pco.gov.ph%',
                                   '%worldbank.org%', '%philstar.com/the-freeman%'])
UNION ALL
SELECT 'route', r.id::text, concat_ws(' | ', r.code, coalesce(nullif(r.name, ''), '(blank)'),
                                      r.vehicle_class, r.operator, 'active=' || r.active::text)
FROM transit_route r
WHERE r.id IN ('52710e90-0b14-4c19-8f59-bf872927d2d4', 'dfae67a9-42e5-4e52-9f48-e9e536c71f59')
UNION ALL
SELECT 'pattern', p.id::text, concat_ws(' | ', r.code, p.direction, p.status,
                                        'signboard=' || coalesce(nullif(p.signboard, ''), '-'))
FROM transit_routepattern p JOIN transit_route r ON r.id = p.route_id
WHERE p.route_id IN ('52710e90-0b14-4c19-8f59-bf872927d2d4', 'dfae67a9-42e5-4e52-9f48-e9e536c71f59')
UNION ALL
SELECT 'route_evidence', e.id::text, concat_ws(' | ', e.pattern_id::text, e.status, e.reviewer,
                                               e.reviewed_at::text, s.title)
FROM transit_routeevidence e JOIN transit_datasource s ON s.id = e.source_id
WHERE e.pattern_id IN ('f7592fc3-21e4-41dd-9977-405cfb4040cc', '704fc96e-2505-462c-9499-8b24ef20fbf8')
ORDER BY 1, 3;
```

**Stop conditions, decided from the pre-check before any write:**
- **Duplicate source:** a `possible_duplicate_source` row with the same URL → reuse that record instead of adding S1–S5.
- **Overlapping fare rule:** any `fare_rule` row for jeepney or modern_puv, regular, with `until=open` → don't end-date it yet. Report it, and the overlap will be reviewed. The planner already treats two overlapping rules of equal scope as Unknown, so leaving it is safe.
- **Route already changed:** the 42D `route` row no longer says `Name missing` → skip step 2.

**Writes, in Django Admin, only after the owner approves:**

| Step | Model | Record | Change |
|---|---|---|---|
| 1 | Data source | S1–S5 (section 3a) | Add five rows, `collected_at` 2026-10-20, license "Unknown — not established" |
| 2 | Route | 42D `52710e90…` | `name`: `Name missing` → *(blank)*. No other field changes, and IDs are kept. |
| 3 | Route evidence | 42D pattern `f7592fc3…` and 17D pattern `704fc96e…` | One `candidate` row each, source S4, with the notes from 3c |
| 4 | Fare rule | Traditional and modern regular (section 3d) | `documented`, `valid_from` 2026-09-28, no end date. Leave route blank: a documented rule may be class-wide, and it never prices. |
| 5 | Record evidence | each rule from step 4 | `documented` rows citing S2 and S3 |

- **Why the rules have no end date:** the temporary *guide* expires on 2026-12-31 (research source 17), but the *rates* do not. So `valid_until` stays blank.
- **What the writes don't touch:** stops, geometry, transfers and statuses.
- **Expected result:** the demo shows "Ride 42D", everything else stays the same, and the fares stay Unknown.
