# Route availability decisions — October 2026

These are product decisions based on Sherilyn's and classmates' commuting
reports. Treat those reports as reliable observations, not official
regulatory confirmation. Historical references do not establish current
frequency or complete route geometry.

## Scarce

Keep these routes available with the badge "Scarce":
01B, 14B, 12K, and 22G.

Source: owner/classmate commuting reports. The Mandaue classmate reported
seeing 22G only rarely. No measured frequency or waiting time is available.

Journeys containing a scarce ride follow ordinary journeys. Preserve the
selected sorting within each group, before applying the result limit.
"not_flagged" means no scarcity report is recorded, not verified frequent service.

## Excluded from suggestions

- 07C, 07E, 12N: classmates reported that these services no longer operate.
- 42D: excluded as Sherilyn's precautionary product decision.

Mango Jeep announced withdrawal of its own 42D service and explicitly
said another operator continued serving that route. This is not evidence
of a confirmed route-wide shutdown.

Supplied announcement:
https://www.facebook.com/InsideCebuPH/posts/990300283523385/

Preserve excluded route records, patterns, stops, fares, and evidence.
Use active=False on confirmed exact records; do not delete records.
Verify 07E's stored identity before any Admin change.

## Unchanged

Leave 14D, 17B, 17D, and 12L unchanged.

Do not infer scarcity or closure from a missing webpage, directory omission,
or replacement of traditional vehicles with modern vehicles.

## Record identity and deployment

Apply decisions to exact Route UUIDs after checking duplicates and patterns.
Route codes are not unique. Do not hardcode route codes or UUIDs in planner logic.

The screenshots show stored records, not confirmation of current operations.
Imported vehicle and operator labels do not independently verify actual fleets
or operators. Keep scarcity provenance separate from route-path evidence.

This document records intended decisions; it does not confirm that production
Admin flags have been applied. Check how a future re-import affects manual flags
before importing again.

## Missing route data

- 42E: the supplied Mango Jeep announcement describes continuing service.
  Keep separate from 42D; never rename 42D or copy its path.
- 03L: historical/directory references identify Mabolo–Carbon; current service
  and usable route data remain to be established.
- 15: owner observed operating on October 23, 2026 (Asia/Manila).
- 15A: owner observed operating on October 23, 2026 (Asia/Manila).

For each addition, establish exact identity, endpoints, supported directions,
ordered boarding/alighting stops, sourced geometry, and distance provenance.
Record operator and vehicle details only where supported. Do not assume 15
and 15A share a path. Names and sightings alone do not establish routable paths.

These additions remain pending and do not block scarcity/exclusion work.

## Mandaue corrections: separate pending data work

A Mandaue classmate reported:
- 21A and 22D terminate around Cathedral/Manalili rather than Carbon.
- The B service reaches Ayala rather than continuing to Carbon; the reported
  code was uncertain between 20B and 21B.
- Former Ouano services now originate at Ibabao.

Preserve these reports without bulk-renaming records or guessing geometry.
Resolve exact route identities, terminals, directions, and ordered stops
before changing planning paths. Later supplied summaries conflict about
21B continuing beyond Ayala, so that detail remains unresolved.