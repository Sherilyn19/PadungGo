# 🚌 PadungGo

## Asa ka padung? PadungGo!

![Open Source](https://img.shields.io/badge/Open%20Source-MIT-green)
![Status](https://img.shields.io/badge/Status-Planning-yellow)
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

**Current status:** documentation and design only. This repository contains no
runnable application or verified transport dataset. Features below are planned.

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
- [Contributing](CONTRIBUTING.md), [changelog](CHANGELOG.md), and [setup](docs/REPOSITORY_SETUP.md)

## 🚌 PadungGo

**Padulong sa imong destinasyon, mas sayon.**

### AI assistance

- Open-weight instruction model
- Hosted open-weight inference API
- Grounded explanation panel for planner results, evidence and uncertainty

The AI explains deterministic results. It does not discover routes, calculate
fares, validate directions or invent missing data. Personal hardware and local
configuration are not part of this project documentation.

### Deployment requirement

PadungGo's competition deliverable must run as a deployed application. Local
development is only for building and testing. Production deployment must include
the frontend, Django API, Supabase PostgreSQL/PostGIS database and hosted AI
inference behind the backend. Ollama may be used privately during development but
is not the production runtime.
