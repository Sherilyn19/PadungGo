# Deployment and operations

The repository supplies a Render Docker blueprint for the API. The configured project uses Vercel for the frontend and Supabase PostgreSQL/PostGIS for the database. These are configuration descriptions, not a guarantee of availability or a claim that every deployed commit matches the checkout.

The [October 24 review](REVIEW_2026-10-24.md) confirmed HTTP responses from the public frontend and API, PostGIS mode in the health response, and a real journey plus AI explanation. No production write or deployment was performed during that review.

## Backend

Use [render.yaml](../render.yaml), [Dockerfile](../backend/Dockerfile), and [startup script](../backend/docker-entrypoint.sh). The image installs geographic libraries, installs Python requirements, and collects static assets. Startup runs migrations, optional administrator bootstrap, then Gunicorn with two workers and a configurable timeout (300 seconds in the blueprint).

Provide a PostgreSQL connection with PostGIS enabled. Keep the database URI and keys in host-managed environment variables. The blueprint uses `PADUNGGO_DB_ENGINE=postgis`, `DJANGO_DEBUG=False`, and documented routing enabled. See [the environment example](../backend/.env.example) for all settings; do not copy its placeholder secret into production.

| Setting | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | A long random deployment secret; Render blueprint generates it |
| `DATABASE_URL` | PostgreSQL connection, with special password characters encoded |
| `FRONTEND_ORIGIN` | Exact permitted browser origins, comma-separated |
| `DJANGO_ALLOWED_HOSTS` | Additional permitted hosts; Render hostname is handled in settings |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Trusted HTTPS origins where needed for Admin |
| `PLANNER_ALLOW_DOCUMENTED` | Whether historical documented patterns may be planned; default False, blueprint True |
| `DRF_NUM_PROXIES` | Trusted forwarding depth; blueprint 3, must match actual host topology |
| `GEOAPIFY_API_KEY` | Optional server-side address and suggestion service |
| `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL` | Optional AI service; see [AI guide](AI_EXPLANATIONS.md) |

Optional `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, and `DJANGO_SUPERUSER_PASSWORD` bootstrap an administrator. An existing account is left unchanged unless the explicit `DJANGO_SUPERUSER_RESET_PASSWORD=True` flag is used. Handle these as credentials; do not leave the one-off reset flag enabled during routine restarts.

The blueprint disables Django's HTTPS redirect because Render terminates HTTPS upstream. Secure cookies and other production settings still apply. Verify proxy headers and HTTPS behavior on a new host before copying this configuration. HSTS starts at 300 seconds; subdomain inclusion and browser preload are disabled. This document does not claim a passing production security audit.

## Frontend

Set Vercel's root directory to `frontend`, build command to `npm run build`, and output directory to `dist`. Set `VITE_API_BASE_URL` to the backend URL ending in `/api/v1`, then rebuild. Allow the exact frontend domain in backend `FRONTEND_ORIGIN`. The current public site is [padung-go.app](https://padung-go.app); the configured API base is `https://padunggo-api.onrender.com/api/v1`.

All `VITE_*` configuration is public. AI and geocoding secrets belong only on the backend.

## Health and operating limits

- `/health` is static liveness, used by the blueprint. It is not a database or provider readiness test.
- `/api/v1/health` adds spatial mode and forwarding-chain counts, not addresses. It also does not test database/provider readiness.
- Default client limits are 120 general requests/minute, 30 plans/minute, 40 place requests/minute, and 6 explanations/minute. These are per-process counters, not strict deployment-wide quotas. Shared addresses can share a limit.
- The network snapshot is process-local, with database-version invalidation. Provider caches are also process-local; daily provider budgets use database counters.
- The free API service may sleep and require a cold start. Hosting quotas and wake times depend on the provider account; no uptime or fixed response-time guarantee is established.
- GTFS uploads default to 50 MB compressed and 500 MB expanded limits. Importing can be expensive; a long worker timeout is not proof of capacity.

Before operating a changed deployment, check a representative journey, origin permissions, administrator access, database connectivity, proxy-depth configuration, and unavailable-provider behavior. Arrange database backups and restoration checks with the hosting provider; these were not inspected in this review. Automated GitHub checks do not deploy or prove production parity.
