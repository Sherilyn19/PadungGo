# 🚌 PadungGo

## Asa ka padung? PadungGo!

![Open Source](https://img.shields.io/badge/Open%20Source-MIT-green)
![Status](https://img.shields.io/badge/Status-MVP%20deployed-blue)
![Hackathon](https://img.shields.io/badge/Cebu%20Hacktoberfest-2026-blue)

> A Cebuano-inspired public transportation assistant that helps
> commuters understand what to ride, where to go, how much it costs, and
> what to expect.

PadungGo is an open-source, location-to-location public transportation journey
planner whose full vision covers journeys **within and across the entire areas
of Cebu City, Mandaue City, and Lapu-Lapu City**, including neighborhoods and
barangays within the same city. Location selection does not guarantee a route.

The **initial hackathon MVP** will demonstrate this vision using a smaller,
verified, interconnected subset of jeepney and bus services. **01K, 23D, 20A,
and 03Q are the initial research batch**, not the permanent network boundary
or proof of current operation. Coverage expands as evidence is verified.

**Current status (October 21, 2026):** a working MVP is deployed.

- **Try it:** https://padung-go.vercel.app (API: https://padunggo-api.onrender.com/api/v1).
  The free API host sleeps when idle, so the first search can take about a minute.
- **Works today:** place search, device location or map tap; direct and
  one-transfer journeys; numbered journey steps; ride lines on the map; an
  independent return trip.
- **Data:** routes come from the Cebu DOTC GTFS archive (2014–2017). They are
  shown as *historic, not field-verified*. No route has been field-verified
  yet. See [Known limitations](#known-limitations).
- **Checks:** GitHub Actions runs the backend tests, a migration check, the
  frontend tests and the production build on every pull request.

Some features described below are still planned; [Known limitations](#known-limitations)
lists what is missing.

## Run locally (Windows PowerShell)

These commands call the virtual environment's Python and `npm.cmd` directly,
so they work even when PowerShell blocks `Activate.ps1` or `npm.ps1` scripts.

```powershell
# Backend (lite SQLite mode; no PostGIS needed)
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env        # then set DJANGO_SECRET_KEY in .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe manage.py runserver   # http://127.0.0.1:8000/health

# Frontend (second terminal)
cd frontend
npm.cmd ci
Copy-Item .env.example .env.local
npm.cmd test
npm.cmd run build
npm.cmd run dev                     # http://localhost:5173
```

A fresh local database has no routes. Import a GTFS feed through Django Admin
or `manage.py import_gtfs`; see [backend/README.md](backend/README.md).
Imported routes are `documented`, so set `PLANNER_ALLOW_DOCUMENTED=True` in
`backend/.env` to see them, as production does.

## Known limitations

- **Current service is not confirmed.** Results come from a historical archive.
  A suggested route may have changed, may run rarely or may no longer run.
  Each result is labelled "Historic data · not field-verified". A planner rule
  based on current-service evidence is designed but not built yet.
- **No frequency or waiting times.** The data has no reliable frequency, so
  waiting time is shown as Unknown. PadungGo never claims a route is frequent.
- **Fares are usually Unknown.** A fare is shown only when a verified fare
  rule, with evidence, names that route. The LTFRB September 2026 PUJ fare
  tables are documented and tested but not yet applied to production routes.
- **Walking is approximate.** Walks are straight-line estimates, not verified
  paths.
- **Location search is curated.** It searches place names imported from the
  feed (about 260 in production). It ignores case, accents, punctuation and
  extra spaces in what you type. Stored names are not normalised: today's
  names have no accents, but a stored name like "Osmeña" would not match a
  typed "osmena".
- **One transfer at most**, and only through transfer points in the data.

## Why PadungGo Exists

Public transportation in Cebu is accessible, but navigating it often
depends on local knowledge.

Commuters commonly ask:

-   Which jeepney or bus should I ride?
-   Where should I board?
-   Where should I get off?
-   How much is the fare?
-   How long will the trip take?
-   What route should I use when returning?

PadungGo organizes verified transportation information into
understandable commuting options.

## Intended Solution

PadungGo provides:

-   GPS, map selection, manual search, and curated location selection
-   Direct and verified one-transfer routes
-   Ideally 3–5 distinct valid alternatives, returning fewer when fewer exist
-   Fare estimation
-   Walking, waiting, and riding duration breakdown
-   Independent return-trip recommendations

The first release prioritizes:

**Accuracy over network size.**

PadungGo will not invent routes or unsupported travel information.

## MVP Features

### Location Selection

Users may select:

-   Current GPS location
-   Map-based origin and destination
-   Manual search
-   Predefined landmarks

### Route Recommendations

Routes are ranked using:

-   Estimated fare
-   Travel duration
-   Number of transfers
-   Convenience

### Travel Breakdown

Each recommendation includes:

-   Walking estimate
-   Waiting estimate
-   Riding estimate

When reliable waiting information is unavailable, the system marks it as
unknown instead of creating false live estimates.

### Return Trip Intelligence

PadungGo independently evaluates:

Destination → Origin

because return routes are not always simple reversals.

## Coverage

Full intended geographic area:

-   Cebu City
-   Mandaue City
-   Lapu-Lapu City

The MVP starts with a verified interconnected subset before expansion. Same-city,
same-barangay and intercity requests use the same planner; no fixed city sequence
is assumed. A geographically valid point may still have no verified journey.

## Architecture

    USER
     |
    React + TypeScript Frontend
     |
    Django REST Framework API
     |
    PostgreSQL + PostGIS
     |
    Verified Transportation Dataset

## Technology Stack

### Frontend

-   React
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui
-   MapLibre GL JS

### Backend

-   Python
-   Django
-   Django REST Framework

### Database

-   Supabase PostgreSQL
-   PostGIS

## Repository Structure

    frontend/  React + TypeScript application
    backend/   Django REST API
    data/      Route datasets and verification references
    docs/      Architecture and documentation
    .github/   GitHub workflows and contribution files

## Data Integrity Principles

PadungGo follows a verification-first approach.

Rules:

-   Only evidence-verified route patterns become trusted
    recommendations.
-   Route codes alone do not define complete transportation information.
-   Third-party datasets must follow licensing rules.
-   Old references should not automatically represent current service.
-   User GPS history is not stored for the MVP.

## Development Roadmap

### Phase 1: Foundation

-   Repository setup
-   Documentation
-   Architecture planning
-   Data model design

### Phase 2: Core System

-   Route database
-   Django API
-   Recommendation logic
-   Fare estimation

### Phase 3: User Experience

-   Interactive map
-   Route visualization
-   Return trip suggestions

### Phase 4: Expansion

-   More verified routes
-   Community contributions
-   Accessibility improvements

## Contributing

Contributions are welcome.

Potential contributions:

-   Route verification
-   Data corrections
-   Documentation
-   Interface improvements

All transportation data contributions must include verification
evidence.

## License

The original PadungGo code and documentation are intended to use the MIT
License.

Third-party transportation data, geographic information, imagery, and
map services remain under their respective licenses.

## Hackathon Context

PadungGo is developed for the Cebu Hacktoberfest 2026 Open Source
Project Competition.

The project follows:

-   Newly initialized repository requirements
-   GitHub hosting
-   Open-source licensing
-   Documentation-first development

The supplied mechanics images require a GitHub repository with a proper license,
a repository submission plus a **1-minute usage video**, and personal attendance
on **October 25, 2026**. Teams may have 1–4 people, so solo work fits that size
rule. If the system incorporates an AI model, it must be open source/open weights;
AI is not required by this design. Judges and named core organizers cannot enter.

The images allocate documentation 30%, technical soundness 60%, and infrastructure
and deployment 10%; originality has no separate weight. These are requirements,
not a claim of implementation compliance. The participant confirms that organizers
allow initialization after October 3 and that registration is complete. The repo
is currently private during development. Submission is due **October 23, 2026,
11:59 PM** (Philippine time used for planning). Plan public release for the
open-source submission. See the [mechanics review and documentation audit](docs/NEXT_STEPS.md).

## Design documents

- [Product requirements](docs/PRODUCT_REQUIREMENTS.md) and [user flow](docs/USER_FLOW.md)
- [Architecture](docs/ARCHITECTURE.md) and [database design](docs/DATABASE_DESIGN.md)
- [API contract](docs/API_DESIGN.md) and [routing algorithm](docs/ROUTING_ALGORITHM.md)
- [Development roadmap](docs/DEVELOPMENT_ROADMAP.md), [data sources](docs/DATA_SOURCES.md),
  and [verification standard](docs/DATA_VERIFICATION.md)
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md), [setup](docs/REPOSITORY_SETUP.md),
  and [submission checklist](docs/SUBMISSION.md)

## 🚌 PadungGo

**Padulong sa imong destinasyon, mas sayon.**

### AI assistance (planned, not implemented)

The deployed application contains **no AI model**. Journey planning is
deterministic. An optional explanation panel was considered: it would use an
open-weight model to explain planner results, and would never discover routes,
calculate fares or fill in missing data. It has not been built.

### Deployment

The competition deliverable runs as a deployed application:

- Vercel serves the frontend.
- Render runs the Django API from Docker.
- Supabase provides PostgreSQL with PostGIS.

Local development is only for building and testing.
