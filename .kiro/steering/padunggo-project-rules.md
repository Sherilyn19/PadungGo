---
inclusion: always
---

# PadungGo project rules

Read this file and `padunggo-status.md` at the start of every session. Global
preferences (readable code, naming, comments, security, credit use, asking
before unclear work) are stored separately as Kiro user learnings.

**Precedence:**
1. The user's explicit instructions
2. Official hackathon rules
3. The attached references below, used as guidance (not every recommendation is mandatory)

## Hackathon: Cebu Hacktoberfest 2026, Open Source Competition

Source: official mechanics images supplied by the user on Oct 19, 2026 (also summarized in README "Hackathon Context").

- **Submission:** the GitHub repository plus a **1-minute video showing how the project is used**, with no pitching. Due **Oct 23, 2026, 11:59 PM (Asia/Manila)**.
- **Requirements:**
  - The project must be fresh. Organizers confirmed that initializing after Oct 3 is allowed.
  - It must be hosted on GitHub with a proper license. MIT is in place.
  - Any AI model built into the system must be open source or open weights. The planner uses none; the optional "Explain this trip" feature uses `openai/gpt-oss-20b` (Apache 2.0) hosted by GroqCloud.
  - The participant must attend in person on **Oct 25, 2026**.
- **Eligibility:** teams of 1–4 people (this is a solo project). Judges and the core organizers (Neriah "BJ" Ato, Sabrinah Yonell Yap, Dorell James Galang) cannot participate.
- **Award categories:** Best Overall Project, Best Use of AI, Most Funny/Best Easter Egg.
- **Repository visibility:** the repo is private now and must be **made public** before submission; check that judges can access it.

### Judging criteria (weights)

| Area | Sub-criteria |
|---|---|
| **Documentation 30%** | Completeness 15, Progress documentation/changelog 5, Contribution readiness 5, Demonstration quality 5 |
| **Technical soundness 60%** | Implementation completeness 15, Solution fit 10, UX & design 10, Security adherence 10, Code quality & structure 5, Codebase tooling 5, Testability 5 |
| **Infrastructure & deployment 10%** | Deployment 5, Scalability 5 |

Flag anything that could break the submission rules, eligibility, the deadline, or the allowed-technology rules.

## Live deployment

- API (Render): https://padunggo-api.onrender.com/api/v1
- Frontend (Vercel): https://padung-go.vercel.app

## Reference guidance (user-supplied attachments)

### "Refactoring and Code Quality" lecture

Apply its relevant principles:
- readable code
- clear responsibilities
- less duplication
- behavior-preserving refactoring backed by tests
- small, incremental changes

It does **not** require splitting every long function or using a particular
folder structure. Split code only where responsibilities justify it.

Rules for refactoring work:
- Run the tests before and after each structural change.
- Keep intentional bug fixes and API changes **separate from refactoring**, and label them as such.

### UXPin "Web UI Design Best Practices"

Use it as practical guidance, not a mandate to implement every example or to
redesign the app. UI exists to help people complete tasks: clarity,
interaction, and feedback, not just appearance. Problems that stop a journey
search come before cosmetic polish.

Improvements worth making:
- clear wording
- consistency
- responsive layout
- accessibility
- loading, error, and empty states

## Repo conventions

- **Branches:** `feat/…`, `fix/…`, `docs/…`, `chore/…`. Never commit to `main`; the user merges PRs.
- **Commits:** Conventional Commits, e.g. `feat(planner): …`.
- **PRs:** one focused change per PR, using `.github/PULL_REQUEST_TEMPLATE.md`.
- **Route data:** stays "Candidate" until it has been reviewed against evidence.
- **Checks:**
  - Backend: `cd backend && python -m pytest`
  - Frontend: `cd frontend && npm test && npm run build`
- **Linters and formatting:** do not add new linters or make widespread formatting changes until the core fixes are stable.

## Approved priorities (Oct 19, 2026)

1. **P0 – baseline.** Run the backend tests and the frontend build.
2. **P0 – security fixes:**
   - Production settings must not depend on detecting test runs.
   - Harden the GTFS upload: enforce the size limit early, check the file type, and guard against zip bombs.
   - `ensure_superuser` must not overwrite an existing password on ordinary restarts, but there must still be a deliberate way to create an admin.
3. **P0/P1 – correctness:**
   - Investigate the stale network cache after imports and fix it if results go out of date.
   - Fix the ignored `area_id` and invalid `limit` handling as explicit bug fixes, and document the API behavior changes.
4. **P1 – tests and CI.** Add focused regression tests, and a CI workflow that uses the existing pytest, vitest, and build tools.
5. **P1 – thorough refactor and documentation:**
   - Split the planner, clean up the importer, organize the frontend, and split `App()` where its responsibilities justify it.
   - Use clear naming, shared logic, and sensible abstractions, preserving behavior.
   - Add meaningful regression coverage.
   - Update the setup and deployment docs, and merge the overlapping roadmaps without losing useful information.
6. **P1 – Kiro/Codex split.** Kiro coordinates and assigns Codex substantial, self-contained work with explicit file ownership. Before the refactor starts, give the user a copy-ready Codex prompt. Review and integrate Codex's work, then run the combined checks.
7. **P1/P2 – UI improvements guided by UXPin:** clarity, consistency, responsive layout, accessibility, and loading/error/empty states, without breaking journey search.
8. **Final steps:** deployment verification and the demo video. Flag schedule tradeoffs instead of silently dropping work.
