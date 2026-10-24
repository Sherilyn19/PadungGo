# Cebu Hacktoberfest 2026: alignment review

Reviewed in a follow-up pass. **PadungGo has strong implementation alignment with the supplied judging categories, but full competition compliance is not independently established.** The application, tests, deployment, documentation, and optional open-weight AI provide concrete evidence. Historical-data rights, current-service verification, attendance, and parts of the submission evidence remain unresolved or unverified.

This is an evidence comparison, not a predicted score or an organizer's eligibility ruling. The general project overview is in the [README](../README.md); dated verification is in the [implementation review](IMPLEMENTATION_REVIEW.md).

## Source and interpretation

The participant supplied eight mechanics images: 1.jpg (event/workshop notice), 2.jpg (mechanics), 3.jpg (requirements), 4.jpg (participant exclusions), 5.jpg (overall criteria), 6.jpg (documentation), 7.jpg (technical soundness), and 8.jpg (infrastructure/deployment). They were inspected in the earlier mechanics review and are not bundled in this repository. They have not been independently authenticated as the organizer's latest rules. The [event website](https://hf26.cebutechcommunities.org) could not be retrieved during review.

The deadline of October 23, 2026, 11:59 PM (Asia/Manila), registration status, and clarification allowing initialization after October 3 were supplied by the participant. The pictured wording alone does not establish those clarifications. Keep organizer confirmation and submission receipts as supporting evidence without publishing private details.

## Mechanics checklist

Checked items mean there is the evidence stated in the last column; they do not imply organizer acceptance.

| Status | Requirement or review concern | PadungGo evidence / remaining uncertainty |
|---|---|---|
| [x] | Team of 1–4 | Participant describes a solo project, within the stated team size. |
| [x] | Fresh project initialized in the event period | Earliest local commit is October 14 (`c55ecd5`). Participant reports organizers allow initialization after October 3, resolving the literal date concern on that basis. |
| [x] | Registration | Participant confirms complete; not independently checked against organizer records. |
| [x] | GitHub repository with proper code license | Public [repository](https://github.com/Sherilyn19/PadungGo), anonymous GitHub API visibility check, and root [MIT license](../LICENSE). |
| [ ] | Third-party rights (release review concern, beyond the pictured code-license wording) | Original code is MIT, but historic Cebu DOTC feed reuse/redistribution rights remain unestablished. Map, model, font, and provider terms remain separate. |
| [x] | AI encouraged, optional; incorporated models must be open source/open weights | Application AI is implemented and a live response identified `openai/gpt-oss-20b`, with an Apache 2.0 open-weight model card. See [AI evidence](AI_EXPLANATIONS.md). Development-assistant use alone would not establish this. |
| [x] | Submit repository plus a one-minute usage video after the development period; no pitches | Participant confirms the video and submission form have been submitted. This review did not inspect the uploaded video, link permissions, runtime, content, receipt, or submission timestamp. Do not list submission as still pending. |
| [ ] | Demo includes actual application use and instructions to run in the repository and video | Repository run instructions are present. Uploaded video content and run-instruction coverage are unverified. No new submission is requested by this review. |
| [ ] | Personally attend the in-person event | Not yet confirmed; distinct from registration and online submission. |
| [ ] | Judges and named core organizers cannot participate | Participant's role was not independently established. The supplied exclusions name Neriah “BJ” Ato, Sabrinah Yonell Yap, and Dorell James Galang, as well as judges. |
| [ ] | Workshop/checkpoint expectations | October 10 notice describes a checkpoint; participant-supplied October 18 text describes a final checkpoint. The supplied evidence does not settle the eligibility consequence of missing checkpoints. Organizer clarification is needed before asserting an exemption or compliance. |

No separate originality weighting or universal requirement to use Kiro, Model Context Protocol, or Agent Client Protocol appears in the supplied mechanics. Workshop examples are not extra judging rules. Best Use of AI and Funniest/Easter Egg are additional recognition categories, not extra percentage weights in the supplied 100% rubric. No Easter Egg implementation or award outcome is established by this review.

## Judging comparison

Weights below reproduce the supplied rubric. Assessment concerns evidence, not an awarded score.

| Category | Weight | Evidence in the current project | Gap or qualification |
|---|---:|---|---|
| Documentation completeness | 15% | Project overview, commuter guide, local setup, architecture, database, API, sources, licensing and deployment guides | Historical feed rights unresolved; supplied reference PDFs/images are not bundled. |
| Changelog / progress | 5% | Git history and [changelog](../CHANGELOG.md) show implementation and review progress | A commit history does not establish checkpoint acceptance. |
| Contribution readiness | 5% | Public repository, MIT, contribution guide, issue/PR templates, automated checks | No claim of external contributor onboarding success. |
| Demonstration quality | 5% | Live frontend/API responses, representative journey and real AI response; submitted video reported | Uploaded video quality, exact duration, accessibility and contents not inspected. |
| Implementation completeness | 15% | Frontend/backend, directional direct and one-transfer search, independent return, map, fare choices, place services, Admin/imports, AI | Partial historic network; no complete times/live arrivals; search is heuristic. |
| Solution fit | 10% | Addresses boarding, alighting, transfer and return-trip questions with explicit uncertainty | Current route operation, safe access and actual fare applicability need stronger evidence. |
| User experience / design | 10% | Map plus numbered steps, incremental alternatives, scarcity/unknown labels, responsive frontend code | No full browser usability/accessibility audit; five-second welcome screen is independent of API readiness; AI fare selections differ. |
| Security | 10% | Validation, Admin authentication, host/origin settings, server-side keys, upload safeguards, throttles and provider budgets | Per-process client limits, proxy dependence, no fresh full-history secret scan or penetration/dependency audit in this review. |
| Code quality / structure | 5% | Separate planner/API/provider modules, typed frontend, domain models and migrations | SQLite checks do not prove all production spatial/database invariants; data review remains manual. |
| Tooling | 5% | Version control, lockfile, pytest, Vitest, TypeScript/Vite build, Docker and GitHub Actions | No separate frontend lint command; build reports a large bundle warning. |
| Testability | 5% | Backend/frontend suites and isolated provider tests; migration consistency checks | No demonstrated browser end-to-end, production PostGIS CI, load test or broad hosted-model evaluation. |
| Deployment | 5% | Public frontend and API responded; API reports PostGIS mode; Vercel/Render/Supabase setup documented | Exact deployed commit parity, backup restoration and uptime not established. |
| Scalability | 5% | Separated services, reusable network schema, network caching, pagination/result limits, provider budgets | In-memory search and per-worker caches/throttles; 40 transfer candidates retained after enumeration; no measured capacity or distributed-load evidence. |

Totals: documentation **30%**, technical soundness **60%**, infrastructure/deployment **10%**.

## Best Use of AI assessment

There is now a real application AI feature, not just AI-assisted development. The server recomputes a selected trip, gives limited planner facts to an open-weight model, validates the answer, and supplies notices. A successful live sample supports implementation alignment with the optional category.

It does not establish that PadungGo will win that category. The feature has narrow scope, heuristic text checks, and a mismatch with passenger/vehicle fare choices. Reliability across routes, usefulness to commuters, and the submitted demonstration remain matters for evidence and judging.
