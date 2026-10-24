# LTFRB PUJ fare guides effective 2026-09-28

## Sources and scope

- Publisher: Land Transportation Franchising and Regulatory Board,
  Department of Transportation, Republic of the Philippines.
- Publisher address printed on both guides: East Avenue, Quezon City.
- Source page supplied by a contributor: https://ltfrb.gov.ph/fare-rates/
- Download date supplied by a contributor: 2026-10-21 (Asia/Manila).
- Local source files: Traditional PUJ.pdf and Modern PUJ.pdf.
- Each PDF contains one page. All references below are to page 1.
- Contributor-supplied download links:
  - https://drive.google.com/file/d/1xBNN-_KPeCwPeeYd4cAx1UtB2wMbA9NO/view
  - https://drive.google.com/file/d/15IcGdAKFdlSAqaCy8SHh759e6OP8mIZF/view

The links are recorded as the supplied pair; their individual mapping to
the local files has not been independently verified. The source webpage
returned HTTP 403 during review, and the Drive pages could not be fetched.
The evidence reviewed was the supplied local PDFs, their extracted text,
and rendered pages, not an independently downloaded replacement.

The PDFs are not bundled in this repository. This record preserves their transcription and review limits; it does not grant rights to redistribute the source files.

## Current application use

The current code uses these rates in a separate **guide estimate**, not as verification that every route has an applicable fare rule. `guide_fares.py` rounds each ride's recorded positive integer metre distance up to a whole kilometre, up to 50 km, then rounds money to the nearest 25 centavos. Bus rides are excluded. The frontend selects Regular or grouped Student/Senior/PWD and traditional, modern, or uncertain vehicle type; uncertain type can show a range. “Modern” is limited by the air-conditioned modern/electric source scope below.

Rounding fractional kilometres upward is an application estimate assumption: the supplied pages do not establish it as official policy. The actual vehicle subtype and billable distance remain unverified. The fixed guide has no automatic detection of a replacement guide.

Evidence-supported fare quotation is a separate path with stricter applicability checks and can remain unknown. Frontend estimates do not make a journey eligible for cheapest ranking, and AI explanations do not use the frontend passenger/vehicle selections.

## Traditional PUJ

Printed title: "PUJ GENERAL FARE GUIDE".
The supplied filename and source-page screenshot identify it as Traditional
PUJ. The printed page names PUJ and does not specify additional subclasses.

Effective date: September 28, 2026.

Page 1 labels the computation "COMPUTATION OF FARES: (Add-on Method)":

| Category | First four kilometres, before rounding | Additional fare per kilometre |
|---|---:|---:|
| Regular | P14.00 | P2.00 |
| Student / Elderly / PWD | P11.20 | P1.60 |

Short extracts, page 1:

- Regular: "First Four (4) kilometers = P 14.00".
- Discounted: "First Four (4) kilometers = P 11.20".
- "NOTE: Fares are rounded off to the nearest 25 centavos".

Fractional-distance handling: **not stated**.
Money-rounding tie handling: **not stated**.

### Complete printed table

Amounts are PHP, transcribed with the printed two decimal places.
"Discounted" means the printed "Student / Elderly / PWD" column.
Old columns are retained for transcription completeness, not for new rules.

| km | Old regular | Old discounted | New regular | New discounted |
|---:|---:|---:|---:|---:|
| 1 | 13.00 | 10.50 | 14.00 | 11.25 |
| 2 | 13.00 | 10.50 | 14.00 | 11.25 |
| 3 | 13.00 | 10.50 | 14.00 | 11.25 |
| 4 | 13.00 | 10.50 | 14.00 | 11.25 |
| 5 | 14.75 | 11.75 | 16.00 | 12.75 |
| 6 | 16.50 | 13.25 | 18.00 | 14.50 |
| 7 | 18.50 | 14.75 | 20.00 | 16.00 |
| 8 | 20.25 | 16.25 | 22.00 | 17.50 |
| 9 | 22.00 | 17.50 | 24.00 | 19.25 |
| 10 | 23.75 | 19.00 | 26.00 | 20.75 |
| 11 | 25.50 | 20.50 | 28.00 | 22.50 |
| 12 | 27.50 | 22.00 | 30.00 | 24.00 |
| 13 | 29.25 | 23.25 | 32.00 | 25.50 |
| 14 | 31.00 | 24.75 | 34.00 | 27.25 |
| 15 | 32.75 | 26.25 | 36.00 | 28.75 |
| 16 | 34.50 | 27.75 | 38.00 | 30.50 |
| 17 | 36.50 | 29.00 | 40.00 | 32.00 |
| 18 | 38.25 | 30.50 | 42.00 | 33.50 |
| 19 | 40.00 | 32.00 | 44.00 | 35.25 |
| 20 | 41.75 | 33.50 | 46.00 | 36.75 |
| 21 | 43.50 | 35.00 | 48.00 | 38.50 |
| 22 | 45.50 | 36.25 | 50.00 | 40.00 |
| 23 | 47.25 | 37.75 | 52.00 | 41.50 |
| 24 | 49.00 | 39.25 | 54.00 | 43.25 |
| 25 | 50.75 | 40.75 | 56.00 | 44.75 |
| 26 | 52.50 | 42.00 | 58.00 | 46.50 |
| 27 | 54.50 | 43.50 | 60.00 | 48.00 |
| 28 | 56.25 | 45.00 | 62.00 | 49.50 |
| 29 | 58.00 | 46.50 | 64.00 | 51.25 |
| 30 | 59.75 | 47.75 | 66.00 | 52.75 |
| 31 | 61.50 | 49.25 | 68.00 | 54.50 |
| 32 | 63.50 | 50.75 | 70.00 | 56.00 |
| 33 | 65.25 | 52.25 | 72.00 | 57.50 |
| 34 | 67.00 | 53.50 | 74.00 | 59.25 |
| 35 | 68.75 | 55.00 | 76.00 | 60.75 |
| 36 | 70.50 | 56.50 | 78.00 | 62.50 |
| 37 | 72.50 | 58.00 | 80.00 | 64.00 |
| 38 | 74.25 | 59.25 | 82.00 | 65.50 |
| 39 | 76.00 | 60.75 | 84.00 | 67.25 |
| 40 | 77.75 | 62.25 | 86.00 | 68.75 |
| 41 | 79.50 | 63.75 | 88.00 | 70.50 |
| 42 | 81.50 | 65.00 | 90.00 | 72.00 |
| 43 | 83.25 | 66.50 | 92.00 | 73.50 |
| 44 | 85.00 | 68.00 | 94.00 | 75.25 |
| 45 | 86.75 | 69.50 | 96.00 | 76.75 |
| 46 | 88.50 | 71.00 | 98.00 | 78.50 |
| 47 | 90.50 | 72.25 | 100.00 | 80.00 |
| 48 | 92.25 | 73.75 | 102.00 | 81.50 |
| 49 | 94.00 | 75.25 | 104.00 | 83.25 |
| 50 | 95.75 | 76.75 | 106.00 | 84.75 |

## Aircon modern and electric PUJ

Printed title: "AIRCON MODERN AND ELECTRIC PUJ GENERAL FARE GUIDE".

Named variants: aircon modern PUJ and electric PUJ. One shared table is
printed. No separate non-aircon modern table or rate is supplied. Do not
infer that this guide covers every vehicle labelled modern_puv.

Effective date: September 28, 2026.

Page 1 labels the computation "COMPUTATION OF FARES: (Add-on Method)":

| Category | First four kilometres, before rounding | Additional fare per kilometre |
|---|---:|---:|
| Regular | P17.00 | P2.40 |
| Student / Elderly / PWD | P13.60 | P1.92 |

Short extracts, page 1:

- Regular: "First Four (4) kilometers = P 17.00".
- Discounted: "First Four (4) kilometers = P 13.60".
- "NOTE: Fares are rounded off to the nearest 25 centavos".

Fractional-distance handling: **not stated**.
Money-rounding tie handling: **not stated**.

### Complete printed table

Amounts are PHP. Column meanings are the same as in the traditional table.

| km | Old regular | Old discounted | New regular | New discounted |
|---:|---:|---:|---:|---:|
| 1 | 15.00 | 12.00 | 17.00 | 13.50 |
| 2 | 15.00 | 12.00 | 17.00 | 13.50 |
| 3 | 15.00 | 12.00 | 17.00 | 13.50 |
| 4 | 15.00 | 12.00 | 17.00 | 13.50 |
| 5 | 17.25 | 13.75 | 19.50 | 15.50 |
| 6 | 19.50 | 15.50 | 21.75 | 17.50 |
| 7 | 21.50 | 17.25 | 24.25 | 19.25 |
| 8 | 23.75 | 19.00 | 26.50 | 21.25 |
| 9 | 26.00 | 20.75 | 29.00 | 23.25 |
| 10 | 28.25 | 22.50 | 31.50 | 25.00 |
| 11 | 30.50 | 24.25 | 33.75 | 27.00 |
| 12 | 32.50 | 26.00 | 36.25 | 29.00 |
| 13 | 34.75 | 27.75 | 38.50 | 31.00 |
| 14 | 37.00 | 29.50 | 41.00 | 32.75 |
| 15 | 39.25 | 31.25 | 43.50 | 34.75 |
| 16 | 41.50 | 33.00 | 45.75 | 36.75 |
| 17 | 43.50 | 35.00 | 48.25 | 38.50 |
| 18 | 45.75 | 36.75 | 50.50 | 40.50 |
| 19 | 48.00 | 38.50 | 53.00 | 42.50 |
| 20 | 50.25 | 40.25 | 55.50 | 44.25 |
| 21 | 52.50 | 42.00 | 57.75 | 46.25 |
| 22 | 54.50 | 43.75 | 60.25 | 48.25 |
| 23 | 56.75 | 45.50 | 62.50 | 50.00 |
| 24 | 59.00 | 47.25 | 65.00 | 52.00 |
| 25 | 61.25 | 49.00 | 67.50 | 54.00 |
| 26 | 63.50 | 50.75 | 69.75 | 55.75 |
| 27 | 65.50 | 52.50 | 72.25 | 57.75 |
| 28 | 67.75 | 54.25 | 74.50 | 59.75 |
| 29 | 70.00 | 56.00 | 77.00 | 61.50 |
| 30 | 72.25 | 57.75 | 79.50 | 63.50 |
| 31 | 74.50 | 59.50 | 81.75 | 65.50 |
| 32 | 76.50 | 61.25 | 84.25 | 67.25 |
| 33 | 78.75 | 63.00 | 86.50 | 69.25 |
| 34 | 81.00 | 64.75 | 89.00 | 71.25 |
| 35 | 83.25 | 66.50 | 91.50 | 73.00 |
| 36 | 85.50 | 68.25 | 93.75 | 75.00 |
| 37 | 87.50 | 70.00 | 96.25 | 77.00 |
| 38 | 89.75 | 71.75 | 98.50 | 79.00 |
| 39 | 92.00 | 73.50 | 101.00 | 80.75 |
| 40 | 94.25 | 75.25 | 103.50 | 82.75 |
| 41 | 96.50 | 77.00 | 105.75 | 84.75 |
| 42 | 98.50 | 79.00 | 108.25 | 86.50 |
| 43 | 100.75 | 80.75 | 110.50 | 88.50 |
| 44 | 103.00 | 82.50 | 113.00 | 90.50 |
| 45 | 105.25 | 84.25 | 115.50 | 92.25 |
| 46 | 107.50 | 86.00 | 117.75 | 94.25 |
| 47 | 109.50 | 87.75 | 120.25 | 96.25 |
| 48 | 111.75 | 89.50 | 122.50 | 98.00 |
| 49 | 114.00 | 91.25 | 125.00 | 100.00 |
| 50 | 116.25 | 93.00 | 127.50 | 102.00 |

## Computation audit

For whole-kilometre rows, use the printed unrounded base, add the printed
increment for each kilometre beyond four, then round the resulting amount
to the nearest 25 centavos. This reproduces all 200 new-fare cells:
50 distances x two guides x two fare categories.

Use these integer-centavo inputs:

| Guide/category | Base | Base distance, m | Increment | Increment distance, m | Rounding |
|---|---:|---:|---:|---:|---:|
| Traditional regular | 1400 | 4000 | 200 | 1000 | 25 |
| Traditional discounted | 1120 | 4000 | 160 | 1000 | 25 |
| Aircon modern/electric regular | 1700 | 4000 | 240 | 1000 | 25 |
| Aircon modern/electric discounted | 1360 | 4000 | 192 | 1000 | 25 |

The discounted policy uses its own explicitly printed base and increment.
Do not use the rounded table minimum as the computation base, and do not
calculate the discount from an already-rounded regular fare.

For example:
- Traditional, 6 km discounted: 1120 + 2 x 160 = 1440, rounded to 1450.
- Modern, 5 km regular: 1700 + 240 = 1940, rounded to 1950.
- Modern, 10 km discounted: 1360 + 6 x 192 = 2512, rounded to 2500.
  Discounting the rounded regular fare of 3150 would instead produce 2520
  before rounding and would not reproduce the published discounted row.

The existing compute_leg_fare_centavos implementation supports reproduction
of the printed whole-kilometre table through rounding_centavos=25. That
arithmetic audit required no calculator or validator change.

The subsequent fare-display change adds quotation safeguards separately from
the calculator. Distance-band quotes require evidence-supported
max_distance_m metadata in the existing policy JSON. The supplied tables cover
through 50,000 metres; this does not establish coverage beyond that distance.
Recording a coverage limit does not by itself establish vehicle applicability
or authorize a rule to be verified or activated.

The quotation layer withholds amounts for unsupported partial increments
above the base distance and unresolved monetary rounding ties. Existing tests
of the calculator's round-up behavior record implementation behavior, not an
official fractional-kilometre policy.

Supported distance-band quotes are labelled Approximate because recorded route
distance does not establish exact billable distance. A supported applicable
flat fare can be classified exact. Passenger categories retain their own
printed policy inputs; discounts are not calculated from an already-rounded
regular fare.

The API provides fare classification and explanatory reasons. The
fractional-distance, discount-wording and vehicle-subtype questions below
remain unresolved.

The regression tests contain literal expected new-table values. They do
not generate expectations from the formula being tested. See the [implementation review](IMPLEMENTATION_REVIEW.md) for test execution results; the arithmetic transcription alone is not a test-run claim.

## Consistency findings and limits

- No unreadable cells were found.
- No new-fare row contradicts its printed add-on formula followed by
  nearest-25-centavo rounding.
- All printed fare columns are nondecreasing and multiples of P0.25.
- The printed computation section specifies the new fares; it does not
  provide the old-fare formulas. Old columns are not used as 2026 policies.
- There is a wording conflict requiring clarification: both guides say
  students receive a discount of "not less than 20% of the approved adjusted
  fare", but some rounded discounted cells exceed 80% of the corresponding
  rounded regular fare.
  - Traditional, 1-4 km: 80% of P14.00 is P11.20; the table prints P11.25.
  - Modern, 6 km: 80% of P21.75 is P17.40; the table prints P17.50.
  These are not failures of the printed add-on and rounding computation.
  Preserve the published cells and ask LTFRB-7 to clarify the wording;
  do not silently substitute a different rounding rule.
- The student footnote says the discount applies every day, including
  Saturdays, Sundays and holidays, and cites MC 2017-024. That circular was
  not independently reviewed for this task.
- Neither PDF states how to charge fractional kilometres. A table of
  integer distances alone does not establish ceil, floor or nearest.
- Neither PDF supplies a separate non-aircon modern rate, a route-specific
  fleet determination, or verification of archived journey distances.
- The supplied tables end at 50 km. Values beyond that range are not
  table-verified by this work.
- No expiry date is printed on either supplied page.

## Answers and review items

- Traditional 4.055 km: **not stated** on page 1. Current ceil behavior
  produces P16.00 with the proposed regular policy, but this is not an
  officially established fare for that fractional distance.
- Aircon modern/electric 5 km: **P19.50 regular / P15.50 discounted**,
  page 1, new-fare table.
- The boundary test at 4,001 m preserves existing implementation behavior;
  it is not an official fractional-distance assertion.
- LTFRB-7 clarification: fractional-distance treatment, discount wording,
  geographic applicability where not explicit, and coverage of any modern
  variant not named by the supplied guide.
- Remaining data review: source-link mapping, route fleet/subtype evidence, route/pattern distance provenance, passenger applicability, and evidence records.
- Synthetic verified test fixtures do not verify production rules. Keep unresolved applicability visible even when the approximate guide feature returns a value.
