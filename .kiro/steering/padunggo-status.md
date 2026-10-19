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

- Oct 19: Review done and plan approved. Steering files went into PR `chore/kiro-steering`.

## Open items

- The Codex handoff prompt must be confirmed before the refactor starts.
