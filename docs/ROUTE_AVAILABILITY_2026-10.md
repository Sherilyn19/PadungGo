# Route availability decisions — October 2026

These are product decisions based on Sherilyn's (the owner's) and classmates'
commuting reports. Treat those reports as reliable observations, not official
regulatory notices. Historical references do not establish current frequency
or complete route geometry. Later reports supersede earlier conflicting ones.

## Scarce

Shown with the badge "Scarce" (list explanation "Scarce: Few jeepneys",
tooltip "Few jeepneys"): **01B, 14B, 12K, 21F, 21G, 22G**.

| Route | Basis (commuting reports) |
|---|---|
| 01B | Classmate: operates only very occasionally. |
| 14B | Owner: not seen for roughly five years; owner kept it as Scarce rather than excluded. |
| 12K | Owner-approved as scarce. |
| 21F, 21G, 22G | Mandaue classmate: very rare; paths have changed (see Mandaue section). |

No measured frequency or waiting time is available, so none is shown.
Journeys containing a scarce ride follow ordinary journeys; the selected
sorting is preserved within each group, before the result limit.
"not_flagged" means no scarcity report is recorded, not verified frequent service.

## Excluded from suggestions (Route.active = False)

| Route | Basis |
|---|---|
| 03C, 03D | Owner explicitly approved exclusion after an ambiguous 03-series report. |
| 03G, 03K | Latest classmate report: inactive (supersedes an earlier positive implication about 03K). |
| 07C | Classmates: no longer operates. |
| 12N | Excluded based on classmate reports. |
| 42D | Owner's precautionary product decision. |

42D: Mango Jeep announced withdrawal of **its own** 42D service and said
another operator continued serving the route
([announcement](https://www.facebook.com/InsideCebuPH/posts/990300283523385/)).
This is not evidence of a confirmed route-wide shutdown.

Excluded records keep their patterns, stops, fares and evidence; nothing is deleted.

## Unchanged

14D, 17B, 17D and 12L: the owner reports these are not scarce. 03L received a
positive operating report but has no stored record (see Missing route data).

Do not infer scarcity or closure from a missing webpage, a directory omission,
or replacement of traditional vehicles with modern vehicles.

## Application status (checked 2026-10-23 through the public API)

- Exclusions: none of 03C, 03D, 03G, 03K, 07C, 12N, 42D appears among
  the 90 active routes.
- Scarcity: live journey plans returned `service_availability: "scarce"` for
  rides on all six scarce routes, with those journeys grouped last.
- 03K stays excluded (inactive) after the owner reconsidered; it is not marked
  Scarce. Its record UUID was not captured.

Route codes are not unique; decisions are applied to exact Route records.
The planner does not hardcode route codes or UUIDs.

### Re-import risk

The GTFS importer can create fresh copies of routes (active, not_flagged)
under a different source title, which would undo these decisions. No re-import
is authorized; review this list before any future import.

## Mandaue corrections

Classmate reports, latest first:
- "20B ug 21B same rana. Ibabao Mandaue to Ayala." Accepted as an Ibabao–Ayala
  service with no Carbon continuation. No active 20B record is stored.
- 21A, 21D, 22A, 22D: from Ibabao via SM Cebu; they stop at the Cathedral and the
  placard says Manalili.
- Mandaue services no longer start at Ouano; they now start at Ibabao.
- 21F, 21G, 22G: very rare; paths have changed (no endpoints given).

What the stored data (Admin export, 2026-10-23) shows:
- 21x ("Ibabao") and 22x ("Ouano") patterns start at the same stop, Cebu North
  Road, and mostly end at M. Logarta Avenue, about 3 km from Ibabao-Estancia.
  No stored stop is at Ibabao.
- All reach the Carbon area. Kamagong Street / J. Solon Drive is about 30 m from
  the Cebu Metropolitan Cathedral bus stop as mapped in OpenStreetMap.
- OpenStreetMap contributors map route 22A as Ouano to Cathedral and 22D as
  Ibabao–Manalili–Cebu City. This agrees with the reports but is not
  verification of current service.

Applied with the Admin action "Switch stops off or on along a stretch" (preview
first, reversible, only the boarding/getting-off switches change; distances,
segments and transfers stay): 21A, 22A, 21D, 22D keep Kamagong Street /
J. Solon Drive as the last Carbon-side stop and switch off the stops after it
up to M. J. Cuenco Avenue & Osmena Boulevard. Set Signboard to "Manalili" on
those four patterns.

Still missing (no geometry invented):
- The Ibabao terminal and the road from Cebu North Road to Ibabao-Estancia.
- The Ayala to Mandaue return for 21B; the stored return never passes Ayala.
- Endpoints for 21F, 21G, 22G.

## Missing route data

| Candidate | Evidence | Status |
|---|---|---|
| 42E | Continuing service implied by the Mango Jeep announcement above. | Needs its own path; never rename 42D or copy its path. |
| 03L | Positive operating report; historical references: Mabolo–Carbon. | No stored record or path. |
| 15, 15A | Owner saw both operating on 2026-10-23 (Asia/Manila). | No stored records; do not assume a shared path. |
| 04B | Owner: not seen for about five years. | Not in the stored dataset; do not invent a record. |
| 04M | Requested as missing. | Unresolved. |
| 11F, 11G | Listed in a supplied document screenshot (11F Inayawan–SM–Ayala via Leon Kilat; 11G Inayawan/Laray–Colon). | Research leads only. |
| 02E | Report: operates via E-Mall toward Plaza; Pier continuation uncertain ("ata"). | Stored record exists; path not reconciled. |

Each addition needs exact identity, endpoints, directions, ordered
boarding/alighting stops, sourced geometry and distance provenance. Names and
sightings alone do not provide routable paths.

Other routes raised in earlier investigation requests remain unresolved and
unflagged. Earlier broad claims about 21A/22A, 06B, 02B, cross-bridge
services, 12G, 01K and 03Q being phased out or scarce were not established.

## References

Historical/background sources (not current-operation confirmation):
- [OpenStreetMap: Public transportation in Metro Cebu](https://wiki.openstreetmap.org/wiki/Public_transportation_in_Metro_Cebu)
- [The Freeman (2023): BRT Phase 1 to affect 22 PUV routes](https://www.philstar.com/the-freeman/cebu-news/2023/03/24/2254048/brt-phase-1-affect-22-public-utility-vehicle-routes-)
- [The Freeman (2021): Modern jeeps on Talisay–IT Park route](https://www.philstar.com/the-freeman/cebu-news/2021/12/13/2147627/modern-jeeps-play-talisay-it-park-route/amp)
- [Cebu Daily News: Talisay e-jeep operator cuts trips](https://cebudailynews.inquirer.net/714106/e-jeep-operator-in-talisay-cuts-down-trips-as-oil-prices-soar)
- CommuteTour directory pages for [12G](https://ph.commutetour.com/ph/routes/cebu-routes/cebu-jeep/12g/) and [03Q](https://ph.commutetour.com/ph/routes/cebu-routes/cebu-jeep/03Q/)
