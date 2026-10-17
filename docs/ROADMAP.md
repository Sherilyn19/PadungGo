# Solo Developer Roadmap

**Planning summary, not completed work.** See
[DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) for canonical gates and criteria.

PadungGo's full vision covers location-to-location journeys within and across
the entire areas of Cebu City, Mandaue City and Lapu-Lapu City. The solo hackathon
MVP demonstrates a smaller verified interconnected subset with direct journeys
and at most one transfer. 01K, 23D, 20A and 03Q are an initial research batch,
not the complete intended network. Geographic selection never guarantees coverage.

| Work phase | Required result |
|---|---|
| Design and eligibility | Consistent documents; registration complete and post-October-3 initialization allowed per participant |
| Evidence readiness | Verified directional patterns, eligible stops and safe connections; no arbitrary route quota |
| Backend and database | Django/DRF, Supabase PostgreSQL/PostGIS, migrations, Admin and validated imports |
| Planner/API | Generic search, sourced fares, honest time components, distinct alternatives and independent returns |
| Frontend | Four input methods for both endpoints, map plus text, accessible errors and limited-coverage messaging |
| Quality and release | Automated checks, tested setup, changelog, deployment, GitHub submission and 1-minute video |
| Coverage expansion | Add verified intra-city and intercity patterns/places without changing route logic |
| Future improvements | Multiple transfers and measured infrastructure improvements after MVP completion |

Test directionality, invalid transfers, unverified exclusions, unknown fare/time
propagation, fewer-than-three results, asymmetric returns, GPS denial and API
failure versus no-results. Synthetic fixtures prove algorithms, not real coverage.

The participant confirms organizers allow initialization after October 3 and
registration is complete. Submission is due **October 23, 2026 at 11:59 PM**
(Philippine time used for planning). The repository is private during development;
plan public release and verify judge access for submission. The pictured October 25
attendance requirement remains a separate event. See [mechanics review](NEXT_STEPS.md).
