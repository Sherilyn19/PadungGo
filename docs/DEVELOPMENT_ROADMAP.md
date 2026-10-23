# PadungGo Development Roadmap

**Planning gates, not completed milestones.** The current repository is documentation
only. Implementation starts after the owner approves the revised design.

## Vision and MVP boundary

The full vision is a location-to-location jeepney/bus planner throughout Cebu City,
Mandaue City and Lapu-Lapu City, for both intra-city (including same-barangay)
and intercity travel. Selecting a point does not guarantee a verified journey.

A solo hackathon MVP demonstrates the same generic system with a smaller verified
interconnected subset, direct rides and at most one transfer. 01K, 23D, 20A and
03Q are the first research batch, not a mandatory or permanent four-route network.
Do not force all three cities into every itinerary or promise full citywide data.

## Delivery gates

| Phase | Work after approval | Required evidence to advance |
|---|---|---|
| 1. Documentation and eligibility | Align requirements, schema, API and algorithm; record confirmed registration, organizer clarification and submission logistics | Consistent documents, recorded decisions, organizer evidence where needed |
| 2. Data readiness | Validate initial directional patterns, stops, walkable connections, geometry, sources, reuse rights and fare rules | At least a demonstrable real connected subset; explicit missing data; no candidate record labeled verified |
| 3. Backend foundation | Scaffold Django/DRF; configure Supabase PostgreSQL/PostGIS; implement models, imports and Django Admin | Reproducible setup, migrations, relationship/spatial constraints and authorized review workflow |
| 4. Planner and API | Implement generic direct and one-transfer search, fare/time services, ranking, deduplication and independent returns | Synthetic direction/transfer/fare/null tests and canonical API contract checks pass |
| 5. Frontend | React/TypeScript/Vite/Tailwind/shadcn/ui/MapLibre; four endpoint methods, options, text directions and maps | Intra-city/intercity flows, GPS denial, limited coverage, unknown estimates and independent return states work |
| 6. Quality and release | Security/accessibility checks, tested install instructions, automated checks, separate deployments where practical, video and changelog | Public reproducible repository, working deployment, 1-minute usage video and completed submission checks |
| 7. Coverage expansion | Add independently verified route variants, stops, neighborhoods and connections | New records pass the same evidence gates; coverage statements updated with limitations |
| 8. Later algorithms/infrastructure | Profile bottlenecks; extend graph search beyond one transfer; add caching or richer service windows when justified | Measured need, maintained correctness and documented operational cost |

Data research may proceed alongside design, but trusted routing cannot bypass
evidence readiness. Avoid fixed route-count quotas: one researched code can have
many directional patterns, and four codes do not prove connected coverage.

## Acceptance and regression checklist

- Same-city, same-barangay and cross-city inputs use the same coordinate planner.
- Stop occurrence order prevents reverse travel and handles loop occurrences.
- One-transfer journeys require a verified accessible connection, not line crossing.
- More than two ride legs are excluded by the MVP policy, not by hardcoded schema.
- Candidate, documented and needs_review records never become trusted guidance.
- Per-leg fare uses sourced policy and route-path distance; missing fare propagates.
- Walking, waiting and riding are separate; unknown waits prevent complete totals.
- Aim for 3–5 distinct options; one or two valid options remain one or two.
- Outbound and return searches can differ or have independently empty results.
- Maps and text agree; keyboard/non-color alternatives and GPS fallback work.
- Sensitive coordinates/secrets stay out of Git, client bundles and logs.
- API/network failures remain distinguishable from actual empty search results.

Use synthetic fixtures for algorithm tests and label them separately from real
transport data. Record actual test commands/results once software exists; do not
claim tests or CI passed before implementation.

## Competition priorities from the supplied images

| Criterion | Weight | Required project evidence |
|---|---:|---|
| Documentation completeness | 15% | Accurate scope, design, source limits and tested setup |
| Progress documentation/changelog | 5% | Meaningful, truthful change history |
| Contribution readiness | 5% | License, contribution guidance and review templates |
| Demonstration quality | 5% | 1-minute usage video showing real behavior and limitations |
| Implementation completeness | 15% | Working coherent MVP |
| Solution fit | 10% | Useful, verified commuter guidance |
| User experience and design | 10% | Understandable accessible journey flow |
| Security adherence | 10% | Validated requests, protected administration/secrets and privacy |
| Code quality and structure | 5% | Clear modular frontend/backend structure |
| Codebase tooling | 5% | Reproducible dependencies, lint/build/test tooling |
| Testability | 5% | Meaningful route, fare and integration tests |
| Deployment | 5% | Accessible deployed application and deployment instructions |
| Scalability | 5% | Generic patterns, spatial indexes and bounded searches |
| **Total** | **100%** | Documentation 30%, technical soundness 60%, infrastructure/deployment 10% |

No separate originality weight is present. A system AI model, if introduced,
must be open source/open weights under the pictured rule; this planner does not
require one. Prioritize correct implementation over speculative AI, extra routes,
accounts, payments, live tracking or premature infrastructure work.

The participant confirms initialization after October 3 is allowed and registration
is complete. Submission is due **October 23, 2026 at 11:59 PM** (Philippine time
used for planning). Plan repository publication, deployment verification and the
1-minute video before that deadline; the repo is currently private. October 25
attendance is separate. See [NEXT_STEPS](NEXT_STEPS.md) for the mechanics review
and remaining product/data decisions.

## Workshop alignment and deadline planning

The owner is unavailable for the October 10/18 workshops because of capstone work.
Kiro, ACP/MCP and open-model workshop themes do not establish mandatory product
features in the supplied material. Confirm missed-checkpoint handling separately;
October 25 attendance remains a distinct requirement. See [immediate priorities
and provisional dated plan](NEXT_STEPS.md#workshop-context-and-immediate-priorities--october-17-2026).
Implementation remains paused until explicitly authorized.


## AI and workshop alignment

The grounded AI explanation ("Explain this trip") is implemented: GroqCloud
serving the open-weight `openai/gpt-oss-20b` (Apache 2.0) behind Django, with no
local runtime (Ollama is not used). The model host stays configurable. The AI panel
explains only planner payloads and is not a second routing engine. Kiro, ACP and MCP may support workshop/development workflows; they are not
required production dependencies under the current design.


## Deployment constraint

The competition deliverable must be deployed and usable remotely. Local-only
screenshots or a local Ollama runtime do not satisfy the target. Deploy the
frontend, Django API, database connection and hosted open-weight AI endpoint;
keep provider credentials server-side. Verify the deployed AI path (one real
explanation on the live site) before recording the video.
