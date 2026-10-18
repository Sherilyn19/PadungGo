# PadungGo Backend

Python 3.11+ (3.12 in production) · Django 5.2 · DRF · Supabase PostgreSQL/PostGIS.

Two database modes:

- **lite** (`PADUNGGO_DB_ENGINE=sqlite`): local development and tests. No GDAL/PostGIS needed.
- **postgis**: production on Fly.io. The Docker image installs GDAL/GEOS/PROJ.

## Local setup (Windows PowerShell)

```powershell
cd backend
py -3.12 -m venv .venv            # or py -3.11
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env       # then set DJANGO_SECRET_KEY in .env
python manage.py migrate
python manage.py createsuperuser  # for /admin
python -m pytest                  # run the test suite
python manage.py runserver        # http://127.0.0.1:8000/health
```

Generate a secret key: `python -c "import secrets; print(secrets.token_urlsafe(50))"`

Local PostGIS mode on Windows requires a GDAL install (OSGeo4W). It is not
needed: Supabase migrations run from the Fly.io image (see below).

## Endpoints

`GET /health`, `GET /api/v1/health`, `GET /api/v1/locations`, `GET /api/v1/routes`,
`GET /api/v1/routes/{id}`, `POST /api/v1/journeys/plan`. Contract: [docs/API_DESIGN.md](../docs/API_DESIGN.md).

## Deploy to Fly.io

1. Supabase: **Database → Extensions → enable `postgis`** (only that one).
2. Install flyctl and log in: `fly auth login`.
3. From `backend/`: `fly launch --no-deploy --copy-config` (keep `fly.toml`;
   if `padunggo-api` is taken, rename it in all four places in `fly.toml`).
4. Set secrets (values are never committed):

   ```powershell
   fly secrets set DJANGO_SECRET_KEY="<generated key>"
   fly secrets set DATABASE_URL="postgresql://postgres.<ref>:<url-encoded-password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
   fly secrets set FRONTEND_ORIGIN="https://<your-app>.vercel.app"
   ```

5. `fly deploy`. The release command runs `migrate` against Supabase.
6. Check: `https://padunggo-api.fly.dev/health`.
7. Admin user: `fly ssh console -C "python manage.py createsuperuser"`.

The AI explanation variables (`AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`) are added
in a later phase.
