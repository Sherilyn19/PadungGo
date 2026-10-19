---
inclusion: always
---

# PadungGo status record

Update this file at the end of each work session, so the next session can continue without repeating discovery.

## Snapshot (Oct 19, 2026)

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
- Backend: a pytest suite.
- Frontend: only `format.test.ts`.
- CI: none yet.

## Hackathon checklist

| Requirement / criterion | Status |
|---|---|
| GitHub repo + MIT license | License ✅. Repo is private and must go public before submission ⏳ |
| 1-minute usage video | ⏳ |
| Submit by Oct 23, 11:59 PM PHT | ⏳ |
| Attend in person Oct 25 | ⏳ (user) |
| Doc completeness / changelog / contribution readiness / demo | Docs are extensive; stale and duplicated sections need fixing ⏳ |
| Implementation completeness / solution fit / UX | End-to-end search is live; UI states need improvement ⏳ |
| Security adherence | P0 fixes in progress |
| Code quality / tooling / testability | Refactor and CI planned |
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

- The frontend bundle is 1.27 MB because of MapLibre. Code splitting is an optional P3 item.
