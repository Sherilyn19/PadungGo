# Local setup and checks

Use Python 3.12 (the production and automated-check version) and Node.js 22 with npm. Python dependencies require 3.11 or later. SQLite mode avoids installing geographic libraries locally; production uses PostGIS. Commands assume a checkout of this repository.

## Windows PowerShell

From the repository root:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env`: replace `DJANGO_SECRET_KEY` with a long random value, keep `PADUNGGO_DB_ENGINE=sqlite` and `DJANGO_DEBUG=True` for local use. Generate a value with:

```powershell
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(50))"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

The API is at `http://127.0.0.1:8000/api/v1`; administration is at `http://127.0.0.1:8000/admin/`. In a second terminal, from the repository root:

```powershell
cd frontend
npm.cmd ci
Copy-Item .env.example .env.local
npm.cmd run dev
```

Open `http://localhost:5173`. Direct Python and `npm.cmd` calls avoid PowerShell activation-script restrictions. Do not overwrite an existing environment file without preserving your settings.

## macOS or Linux

From the repository root:

```sh
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

Edit the same local settings described above, then:

```sh
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(50))'
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver
```

In a second terminal, from the repository root:

```sh
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

## Data and optional services

A fresh database contains no transport network. The `data/` directories are placeholders, not an installable dataset. Obtain a feed with suitable permissions and review its provenance before importing. See [backend import instructions](../backend/README.md) and [data rights](DATA_SOURCES.md).

Imported GTFS records are `documented`, not `verified`. To explore historical data locally, set `PLANNER_ALLOW_DOCUMENTED=True`; the application must retain its historic-data notices. The default is False. Never promote records just to make results appear.

No provider keys are needed to start the app. Without Geoapify configuration, suggestions use stored locations and address labels can be unavailable. Without AI configuration, explanations are unavailable but the planner remains usable. See [deployment settings](DEPLOYMENT.md) and [AI explanations](AI_EXPLANATIONS.md).

`VITE_API_BASE_URL` in `frontend/.env.local` should point to `http://127.0.0.1:8000/api/v1`. All `VITE_*` values are public in the browser bundle. Keep secrets in the backend environment and out of Git.

## Checks

From `backend/`, in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe manage.py check --settings=config.test_settings
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run --settings=config.test_settings
```

On macOS/Linux, replace the interpreter path with `.venv/bin/python`. The pytest configuration selects isolated SQLite test settings and disables real provider keys. The explicit settings above keep checks away from the production database.

From `frontend/`:

```powershell
npm.cmd test
npm.cmd run build
```

Use `npm` on macOS/Linux. The build includes TypeScript checks. [GitHub Actions](../.github/workflows/ci.yml) runs tests, the migration check, and the frontend build on pull requests and pushes to main. It does not deploy. There is no separate lint command in the current frontend scripts.

See the [review record](REVIEW_2026-10-24.md) for dated results and what these checks do not cover.
