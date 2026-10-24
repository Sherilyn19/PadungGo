# Route availability decisions — October 2026

These are maintained product decisions based on commuter reports. They are reported observations, not independently verified regulatory notices. Historical references do not establish current frequency
or complete route geometry. Later reports supersede earlier conflicting ones.

## Scarce

Shown with the badge "Scarce" (list explanation "Scarce: Few jeepneys",
tooltip "Few jeepneys"): **01B, 03K, 14B, 12K, 21F, 21G, 22G**.

| Route | Basis (commuting reports) |
|---|---|
| 01B | Commuter report: operates only very occasionally. |
| 03K | Latest commuter report (Oct 24, 2026): it operates, so the maintainer re-included it as Scarce. This supersedes the earlier "inactive" report. |
| 14B | Maintainer report: not seen for roughly five years; maintainer kept it as Scarce rather than excluded. |
| 12K | Maintainer-designated as scarce. |
| 21F, 21G, 22G | Mandaue commuter: very rare; paths have changed (see Mandaue section). |

No measured frequency or waiting time is available, so none is shown.
Journeys containing a scarce ride follow ordinary journeys; the selected
sorting is preserved within each group, before the result limit.
"not_flagged" means no scarcity report is recorded, not verified frequent service.

## Excluded from suggestions (Route.active = False)

| Route | Basis |
|---|---|
| 03C, 03D | Maintainer excluded the records after an ambiguous 03-series report. |
| 03G | Latest commuter report: inactive. |
| 07C | Commuter reports: no longer operates. |
| 12N | Excluded based on commuter reports. |
| 42D | Maintainer's precautionary product decision. |

42D: Mango Jeep announced withdrawal of **its own** 42D service and said
another operator continued serving the route
([announcement](https://www.facebook.com/InsideCebuPH/posts/990300283523385/)).
This is not evidence of a confirmed route-wide shutdown.

Excluded records keep their patterns, stops, fares and evidence; nothing is deleted.

## Unchanged

14D, 17B, 17D and 12L: commuter reports indicate these are not scarce. 03L received a
positive operating report but has no stored record (see Missing route data).

Do not infer scarcity or closure from a missing webpage, a directory omission,
or replacement of traditional vehicles with modern vehicles.

## Recorded application checks (October 23–24, 2026)

These are dated checks recorded by prior maintainers, not a new database census in the documentation review. Later data changes may supersede them.

- Exclusions: none of 03C, 03D, 03G, 07C, 12N, 42D appears among the active
  routes (checked 2026-10-23 on 90 routes; the 2026-10-24 list has 91, the extra
  one being 03K, see below).
- Scarcity: live journey plans returned `service_availability: "scarce"` for
  rides on all six scarce routes, with those journeys grouped last.
- 03K was re-included as Scarce on 2026-10-24 (maintainer decision after a new
  commuter report). Checked the same day through the public API: a live plan
  (Fuente Osmena to Colon) returned a 03K ride with `service_availability: "scarce"`
  and `has_scarce_ride: true`. The 03K record in the list is "MABOLO - AYALA -
  COLON - SM - NORTH BUS". Whether this is the original record or a re-imported
  copy was not determined; see the re-import risk below.

Route codes are not unique; decisions are applied to exact Route records.
The planner does not hardcode route codes or UUIDs.

### Re-import risk

The GTFS importer can create fresh copies of routes (active, not_flagged)
under a different source title, which would undo these decisions. Review this list and reconcile exact record identities before any future import.

## Mandaue: the return leg stops short (Oct 24 check)

An Admin export of 21A, 21D, 22A and 22D, plus live searches, shows each route is **one pattern** (direction "Unspecified") that holds both legs: out from Ibabao through Mandaue to the Carbon area, a turn-around of six stops that cannot be boarded or left, then a return leg north. The return leg **ends at M. Logarta Avenue**, about 3 km before Ibabao, so a trip from downtown Cebu to the Ibabao side of Mandaue has nowhere to get off. Checked live: boarding at Imus Avenue (a return-leg stop) reaches M. Logarta Avenue, but not the Mandaue City Police Office or Ibabao; Mandaue Police Office to Colon Obelisk works (21A, 21D, 22A, 22D). So the fix is stop data for the end of the return leg, not a larger search radius.

## Mandaue corrections

Commuter reports, latest first:
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

The prior maintenance record reports applying the Admin action "Switch stops off or on along a stretch" (preview
first, reversible, only the boarding/getting-off switches change; distances,
segments and transfers stay): 21A, 22A, 21D, 22D keep Kamagong Street /
J. Solon Drive as the last Carbon-side stop and switch off the stops after it
up to M. J. Cuenco Avenue & Osmena Boulevard. Set Signboard to "Manalili" on
those four patterns.

Ibabao start (draft from OpenStreetMap): contributors map routes 22A and 22D with
the same first stop, C. M. Cabahug (10.3244, 123.9502), and the stretch up to
Ginebra San Miguel meets the stored start (Cebu North Road) about 90 m away.
The available Admin action "Add stops at the start from an OpenStreetMap route (preview
first)" can add those 12 stops, with road distances and shape from the map, in front
of the selected routes. The October 24 documentation review did not independently verify the production state of this extension. Source: OpenStreetMap relation 3208066 (ODbL, credit
OpenStreetMap contributors). Stored as documented, not field-verified. 21A and
21D have no OpenStreetMap route of their own; they share the corridor, so the
same stretch is used. OpenStreetMap's 22A takes a different road via SM City Cebu
after Subangdaku; that variant is not modelled.

Still missing (no geometry invented):
- The exact boarding spot in Ibabao-Estancia (the OpenStreetMap start is the best
  available, not field-checked).
- The Ayala to Mandaue return for 21B; the stored return never passes Ayala.
- Endpoints for 21F, 21G, 22G.

## Missing route data

| Candidate | Evidence | Status |
|---|---|---|
| 42E | Continuing service implied by the Mango Jeep announcement above. | Needs its own path; never rename 42D or copy its path. |
| 03L | Positive operating report; historical references: Mabolo–Carbon. | No stored record or path. |
| 15, 15A | A contributor reported seeing both operating on 2026-10-23 (Asia/Manila). | No stored records; do not assume a shared path. |
| 04B | Maintainer report: not seen for about five years. | Not in the stored dataset; do not invent a record. |
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
