# Changelog

Significant changes will be recorded here as development occurs. Do not backdate entries or fabricate development history.

## Unreleased

### Security and correctness fixes — October 19, 2026

**Security**
- **Production settings:** they no longer guess from the command line whether tests are running. Before, that guess could enable the dev secret key and skip the HTTPS/secure-cookie settings. Now the security settings depend only on `DJANGO_DEBUG`, and the server refuses to start in production without a real secret key. Tests use `config/test_settings.py`.
- **GTFS upload:**
  - Oversized uploads are refused from the `Content-Length` header (413) before Django reads the body.
  - The file must have a `.zip` extension and its contents must really be a zip archive.
  - Archives are rejected if they have too many files or would unzip to more than the size limit (zip-bomb guard).
- **`ensure_superuser`:** it no longer resets an existing admin's password on every restart. A deliberate reset needs `DJANGO_SUPERUSER_RESET_PASSWORD=True` or `--reset-password`.

**Correctness**
- **Stale journey results:** before, an import or admin edit refreshed only the one process that made it. Other workers, or every worker after `manage.py import_gtfs`, kept serving old journeys for up to 5 minutes. A shared `NetworkDataVersion` counter (migration `0003`) now makes every worker reload on its next request.
- **API behavior changes:**
  - `/locations` and `/routes` return 400 for an invalid `limit` or a malformed `area_id` or `cursor`.
  - `area_id` now filters `/routes`.
  - `cursor` pagination now works. Details are in docs/API_DESIGN.md.

**Tests**
- Added 33 regression tests covering the changes above.

**HSTS**
- Verified the live setup before enabling it: valid certificates on both hosts, HTTP redirects to HTTPS on both, and the API serves over TLS 1.3.
- The API now sends `Strict-Transport-Security: max-age=300`, a short starting duration that is configurable with `DJANGO_SECURE_HSTS_SECONDS`.
- `includeSubDomains` and `preload` stay disabled.

### Added
- Initial project concept, architecture, open-source contribution guidance and data-verification standards.

### Changed — October 17, 2026
- Distinguished full intra-city/intercity coverage vision, verified MVP subset and initial four-route research batch.
- Aligned the seven core documents, direction-aware schema, shared versioned API, independent returns and 3–5 distinct alternatives when available.
- Standardized unknown fare/time behavior and preserved detailed routing guidance.
- Visually reviewed all eight supplied mechanics images and recorded eligibility uncertainty, implementation gaps, audit and consistency review in docs/NEXT_STEPS.md.
- Updated supporting architecture, setup and data notes; no application code was added.

### Updated after participant clarification — October 17, 2026
- Recorded completed registration, intentionally private development repository, organizer permission to initialize after October 3, and October 23 at 11:59 PM submission deadline (Philippine time used for planning).
- Removed the resolved initialization-date blocker and retained public-release/submission and October 25 attendance tasks.
- Added a sourced, limited JeepMe/JTransit reference review; no competitor code or transport data imported.
- The earlier documentation ZIP remains a historical snapshot; repository documents contain these latest updates.

### Research update — October 17, 2026
- Recorded the owner's references-first/selective-code-reuse decision.
- Reviewed CommuteTour and Cebu Jeepneys for 01K, 03Q, 20A and 23D; recorded source links, variant/alias questions, licensing, connectivity hypotheses and verification gaps.
- Flagged outdated fare references and the need for the applicable current LTFRB matrix; no routes, fares, coordinates, third-party code or map assets imported.

### Reference and planning update — October 17, 2026
- Added Suroy's guide as a secondary reference with metadata/fare-currency caveats; no operational data imported.
- Recorded workshop nonattendance, distinguished workshop tooling themes from explicit competition requirements, and retained the checkpoint-attendance uncertainty.
- Added immediate evidence/scope/deployment planning priorities and a provisional schedule through October 23; implementation remains unstarted.

### Planned
- Initial route dataset after evidence review.
- Django REST API and database migrations.
- React map, GPS and location selectors.
- Direction-aware itinerary search, alternative ranking, fare estimates and time breakdowns.
- Test suite and production deployment.

### Stack update — October 17, 2026
- Added an open-weight AI explanation layer and documented Hosted open-weight inference API.
- Kept personal hardware and local configuration private; no device specifications were added to repository documentation.
- Kept the deterministic planner authoritative and Kiro/ACP/MCP as optional workshop/development context.

### Deployment clarification — October 17, 2026
- Recorded that the competition deliverable must be deployed and usable remotely.
- Reclassified Ollama as optional development tooling; production AI must use a hosted open-weight inference path behind Django.
