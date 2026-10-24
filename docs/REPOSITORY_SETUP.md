# PadungGo — GitHub Repository Setup

**Participant update, October 17, 2026:** organizers allow initialization after October 3; registration is complete. This resolves the previously flagged initialization-date concern. The repository is currently private during development. Submission deadline: **October 23, 2026 at 11:59 PM**, using Philippine time for planning. See [mechanics review](NEXT_STEPS.md).

## GitHub new-repository fields

- **Repository name:** `padunggo` (a repository name within your own GitHub account; check for naming conflicts separately)
- **Display name:** PadungGo
- **Description:** Open-source Metro Cebu commuter route planner with verified jeepney and bus directions, multiple journey options, fares, and interactive maps.
- **Visibility:** Currently private, as confirmed by the owner. Plan to make the repository public for the open-source submission and verify judge access before the deadline; no visibility change has been performed.
- **Default branch:** `main`
- **License:** MIT (applies to original project material; check third-party data and map terms separately)
- **Topics:** `cebu`, `cebuano`, `public-transport`, `jeepney`, `route-planner`, `react`, `typescript`, `django`, `python`, `open-source`
- **Website:** https://padung-go.app (deployed MVP).

The documentation ZIP includes a root README and LICENSE, but is not a runnable application or a full repository export. If uploading the starter files to an empty GitHub repo manually, do **not** also auto-generate a competing README or LICENSE when creating it; use the included files. Never commit passwords, `.env` credentials, personal GPS histories or secrets.

## Current status

*Updated October 21, 2026.* A runnable MVP is deployed:

- Frontend on Vercel, API on Render, database on Supabase PostGIS.
- CI runs backend tests, a migration check, frontend tests and the build.
- Route data is historical (Cebu DOTC GTFS archive), labelled "not field-verified". **No route data has been validated against current operation.**

Local setup: see the root [README](../README.md#run-locally-windows-powershell). Registration is complete per the participant. Making the repository public, the final submission and October 25 attendance remain open; see [SUBMISSION.md](SUBMISSION.md).

## Brand

**PadungGo**  
*Asa ka padung? PadungGo!*
