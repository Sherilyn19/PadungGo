# PadungGo

**Asa ka padung? PadungGo!**

PadungGo is an **open-source, Cebuano-inspired public transportation journey planner** being developed for a limited, **verified and interconnected** set of routes across Cebu City, Mandaue City, and Lapu-Lapu City, Philippines.

> **Project status: planning and data verification.** This repository is a documentation-first starter; it does not yet offer a working journey planner or verified journey recommendations.

## Problem

Commuters who depend on jeepneys and buses may not know which vehicle to board, where to alight, where to transfer, how much to prepare for fares, how long a journey could take, or which route to use on the way home.

## Intended solution

A mobile-first web app that recommends documented, direction-aware commuting options, including separate outward and return journeys. The intended first release prioritizes **accuracy over network size**; it will not assume all Metro Cebu routes are covered.

### Proposed MVP

- Select **origin and destination** through **GPS**, **search**, **tapping a map**, or **choosing a curated location**. GPS requires permission, and all methods fall back to manual selection.
- Display direct and, where verified, one-transfer jeepney/bus journeys.
- Rank up to several genuinely valid alternatives by **cost**, **estimated duration**, and **fewest transfers**. Do not invent alternatives.
- Independently calculate and suggest **return-trip** alternatives (B → A).
- Show appropriate boarding, transfer and exit locations with a visual route map.
- Display **per-leg and total estimated fare**, with fare-rule source/effective date.
- Separate **walking**, **waiting**, and **riding** duration estimates. When scheduling or frequency evidence is unavailable, mark waiting time **unknown** rather than invent a live ETA.
- Show route variant, source evidence, last-verified date and a clear warning for unavailable or incomplete information.

## Planned technology stack

| Layer | Technology |
| --- | --- |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui |
| Interactive maps | MapLibre GL JS, policy-compliant basemap provider |
| Backend and API | Python, Django, Django REST Framework |
| Database | PostgreSQL on Supabase; PostGIS as appropriate |
| Data curation | Django Admin; reviewed sources and evidence |
| Tests | pytest / pytest-django; Vitest / Playwright |
| Deployment | React frontend and Django backend as separate hosted services |
| Collaboration | GitHub, GitHub Actions (planned) |

The routing engine will begin with direction-aware direct and one-transfer itinerary enumeration in Python. More complex algorithms and GeoDjango tooling are optional later improvements, not prerequisites.

## Planned repository layout

```text
frontend/      React + TypeScript application (to be scaffolded)
backend/       Django REST API and route verification administration (to be scaffolded)
data/          Dataset templates / source rights / verification guidelines
docs/          Architecture, roadmap, data sources and verification
.github/       Contribution and issue templates
```

## Data integrity and coverage

- **Only evidence-verified current route patterns** should be presented as trusted suggestions.
- A route *code* alone does not uniquely identify its direction, vehicle type, operator or variant.
- Old GTFS feeds and community guides may inform research but must not be represented as verified 2026 service.
- Never copy or distribute third-party route datasets unless their terms permit it.
- No commuter's GPS history is required to be stored for the MVP.

See [Data Verification](docs/DATA_VERIFICATION.md) and [Data Sources](docs/DATA_SOURCES.md) before importing transportation records.

## Setup

**No runnable frontend or backend has been scaffolded yet.** Future installation steps will go here only after they have been tested. Avoid treating this starter as a released application.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Route additions and corrections must include sufficient verification evidence; do not submit unverifiable data as authoritative.

## Competition note

This starter is prepared for the **Cebu Hacktoberfest 2026 Open Source Project Competition**. The participant reports that organizers clarified projects must **not have been created before October 3, 2026**; a genuinely new repository created afterward satisfies that date restriction. Registration and the exact submission deadline must still be confirmed. No development dates should be misrepresented.

## License

The **original PadungGo application code and original project documentation** are intended to be available under the [MIT License](LICENSE). **Third-party route, geographic, imagery and basemap content remains subject to its own licenses and service policies.**
