---
inclusion: always
---

# PadungGo status record

Update this file at the end of each work session, so the next session can continue without repeating discovery.

## Snapshot (Oct 21, 2026; `main` = 47cd42a)

**What the app is:** a jeepney/bus journey planner for Metro Cebu.
- Backend: Django + DRF, using PostGIS (or SQLite in lite mode), deployed on Render.
- Frontend: Vite + React 19 + TypeScript, with MapLibre and Tailwind, deployed on Vercel.

**Request flow:**
1. `PlaceInput` calls `GET /api/v1/locations`.
2. `App` calls `POST /api/v1/journeys/plan`.
3. The backend runs `planner/engine.plan_journeys`, then `api/geometry` adds ride geometry.
4. `Results` and `MapView` render the options.

**Data:** loaded through the GTFS importer, either from the admin upload page or with the `import_gtfs` command.

**Tests:**
- Backend: pytest, 434 passing at 47cd42a (owner's local run, same tree as the #23 head).
- Frontend: Vitest, with `api.test.ts`, `format.test.ts` and `journeySteps.test.ts`.
- CI: GitHub Actions (`.github/workflows/ci.yml`) runs pytest, `makemigrations --check`, `npm test` and `npm run build` on every PR.

**Production data:** 97 active routes and about 257 locations, all imported from the DOTC archive as `documented`. **0 verified patterns.** `PLANNER_ALLOW_DOCUMENTED=True` on Render (owner decision), so every live result is historical and labelled.

## Hackathon checklist

| Requirement / criterion | Status |
|---|---|
| GitHub repo + MIT license | License ✅. Repo is private and must go public before submission ⏳ |
| 1-minute usage video | ⏳ |
| Submit by Oct 23, 11:59 PM PHT | ⏳ |
| Attend in person Oct 25 | ⏳ (user) |
| Doc completeness / changelog / contribution readiness / demo | Docs are extensive; stale and duplicated sections need fixing ⏳ |
| Implementation completeness / solution fit / UX | End-to-end search live; journey steps, loading, reduced motion and empty states done (#21). Current-service rule designed, not built ⏳ |
| Security adherence | P0 fixes merged (#10, #12). Credential review: no findings so far; secret scanning must be enabled once public ⏳ |
| Code quality / tooling / testability | Backend refactor (#14) and CI (#11) done ✅ |
| Deployment / scalability | Render + Vercel are live; cache scaling under review |

## Work log

**Oct 19**
- Finished the review; the plan was approved.
- Opened PRs:
  - #9: steering files.
  - #10 (`fix/security-and-correctness`): security fixes for settings, GTFS upload and `ensure_superuser`; the cross-process cache fix (`NetworkDataVersion`, migration 0003); the limit/area_id/cursor API fixes. 104 backend tests pass.
  - #11 (`chore/ci`): GitHub Actions running pytest, the migration check, vitest and the build. Green.
- Baseline before the fixes: backend 71 passed; frontend 4 tests passed and the build worked (1.27 MB JS chunk warning).
- PRs #9, #10 and #11 merged (`main` = ba5f8b8). #10 is live: `limit=abc` returns 400.
- Production HTTPS verified: valid certificates, and HTTP→HTTPS redirects on Render (301) and Vercel (308). PR #12 enables HSTS at `max-age=300`, with includeSubDomains and preload off. Raise the duration gradually after deploying.
- The user decided to **keep the `DJANGO_SUPERUSER_*` env vars on Render**. This is harmless now: existing accounts are never reset unless `DJANGO_SUPERUSER_RESET_PASSWORD=True` is set. Do not ask to remove them again.
- Local test venv: `/projects/sandbox/.venv`. It is not persisted, so recreate it with `python3 -m venv` and `pip install -r backend/requirements.txt`.

**Oct 20–21**
- Merged (squash):
  - #15 place-search input;
  - #16 API-unavailable messages;
  - #17 placeholder route names;
  - #18 17D/42D audit;
  - #19 verified fare-rule safeguards (migration 0004);
  - #20 LTFRB 2026 fare-guide tests;
  - #21 journey steps UI;
  - #22 location-search normalisation;
  - #23 transfer-stop validation.
- The owner completed the mobile, keyboard and reduced-motion checks for #21.
- **14B / current service (unresolved):** the owner reports 14B is hard to find. This is an availability concern, not proof it is inactive. Design decisions so far:
  - a rejected source is not an exclusion decision;
  - expired or unsupported verified patterns are excluded, not downgraded;
  - strict mode requires a reviewer-set deadline, with timestamp-vs-whole-day semantics still to be decided;
  - field evidence or an official/operator publication can support a review, but neither verifies a pattern by itself;
  - frequency is a separate, unmet requirement.

  Deadline renewal and its interaction with verified fare rules still need assessing. Explicit exclusion already works through `Route.active=False` or pattern `needs_review` in Admin.
- **Timezone:** `views.py` uses `date.today()`. Django sets the process TZ from `TIME_ZONE`, so this is probably already Manila time. A separate assessment is pending; it is not a confirmed defect.
- **Credential review:**
  - History (all branches and PR heads), merge-resolution content, 21 PR/issue comments and 31 CI run logs scanned with gitleaks plus pattern searches. No credentials found; only placeholders and masked GitHub tokens.
  - The secret-scanning API returned 403 to Kiro.
  - Not covered: Render, Vercel and Supabase dashboards.
- Deleted branches: `feat/fare-guide-2026`, `feat/journey-steps-ui`, `fix/location-search-tokens`. Five other merged branches have been verified as fully integrated.

**Oct 21 (UI redesign, PR #27, `feat/ui-redesign`)**
- The design reference is the owner's blue "Retro-OS UI kit" image; JeePMe is a usability benchmark only.
- New frontend layout:
  - `components/{layout,search,results,map,ui}`, `hooks/`;
  - `tripTimeline.ts` replaces `journeySteps.ts`.
- Dependencies added: `lucide-react` (ISC) and `@fontsource/pixelify-sans` (OFL).
- API change, approved by the owner's explicit "remove the five-option limit": `limit` max is 50. The frontend falls back to 5 until Render deploys it.
- Fare gap: production has 0 verified patterns, so every fare is "Ask the driver". A frontend LTFRB-guide estimate was deliberately **not** added. It would bypass the #19 safeguards and is waiting on an owner decision.
- QA: headless Chrome via `agent-browser`. HOME must be writable, and `/tmp` is wiped between calls. The live API's CORS blocks localhost, so use a Vite preview proxy.

- Owner follow-up (same PR): accordions replaced with a `TripDetails` child panel (`components/trips`).
  - The panel uses the shared `useResizablePanel` + `ResizablePanel`/`PanelResizeHandle`.
  - `InfoTip` was removed: the owner wants no technical text, not hidden text.
  - Ride palette is in `tripTimeline.ts` (`RIDE_PALETTE`).
  - Owner runs PowerShell, with execution policy blocking `npm.ps1`; use `npm.cmd`. Repo path: `C:\Sherilyn\Hacktob\PadungGo`.

## Work split (confirmed Oct 19)

| Area | Owner | Files |
|---|---|---|
| Backend refactor | Codex (the user applies the edits by hand), branch `refactor/backend-structure` from `ba5f8b8` | `backend/**` only |
| Frontend organization, splitting `App()`, UI/UX improvements, frontend tests | Kiro, branch `refactor/frontend-structure` | `frontend/**` |
| Docs consolidation, CHANGELOG, root README | Kiro | `docs/**`, `README.md`, `CHANGELOG.md` |
| Integration, combined checks, deployment check, demo-video plan | Kiro | none |

- **Shared interface:** the HTTP API contract in `docs/API_DESIGN.md` is frozen. Any frontend need for a backend or API change must be coordinated explicitly with the user before either side changes it.
- **How Codex delivers:**
  - Codex asks its clarifying questions first.
  - It does not run commands. It gives the user exact edits: a clickable file path, an exact Ctrl+F "find" text, and the replacement text, or full contents for new files. It delivers in batches.
  - The user applies the edits, then runs the listed checks or asks Kiro to run them.
  - Kiro reviews the PR and runs the combined checks.

## Open items

- Submission tasks: see `docs/SUBMISSION.md` (public release, video, form, Oct 25 attendance).
- Verify that production runs 47cd42a or later.
- Current-service eligibility rule (PR 2): waiting on the open decisions above.
- The frontend bundle is 1.27 MB because of MapLibre. Code splitting is an optional P3 item.

## Fare estimates (Oct 22, 2026)

- Owner decisions: per-ride Traditional/Modern/Not sure (range); ceil each ride's km; Regular/Student/Senior/PWD (guide's discounted column); older route distances OK for "Estimated"; verified fares keep priority.
- Contract: each ride segment gets `guide_fare_estimate` {status, reason, guide_effective_date, chargeable_km, known_vehicle_type, amounts_centavos{traditional,modern}{regular,discounted}}. Frontend type: `frontend/src/api.ts`.
- Ownership: Kiro = `frontend/**` (PR #30, draft, branch `feat/fare-estimates`). Codex = `backend/**` + `docs/API_DESIGN.md` on `feat/fare-estimates-backend`. Merge backend first.
- Known gaps: the Modern table is aircon modern/electric only; the LTFRB "not less than 20%" wording conflict is unresolved (we use printed cells); there is no evidence of per-route vehicle type.
