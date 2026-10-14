# 🚌 PadungGo

## Asa ka padung? PadungGo!

![Open Source](https://img.shields.io/badge/Open%20Source-MIT-green)
![Status](https://img.shields.io/badge/Status-Planning-yellow)
![Hackathon](https://img.shields.io/badge/Cebu%20Hacktoberfest-2026-blue)

> A Cebuano-inspired public transportation assistant that helps
> commuters understand what to ride, where to go, how much it costs, and
> what to expect.

PadungGo is an open-source web-based public transportation journey
planner designed for a limited, verified, and interconnected set of
routes across Cebu City, Mandaue City, and Lapu-Lapu City.

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
-   Multiple valid alternatives when available
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

Initial coverage:

-   Cebu City
-   Mandaue City
-   Lapu-Lapu City

The project starts with a verified interconnected corridor before
expansion.

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

-   PostgreSQL
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

## 🚌 PadungGo

**Padulong sa imong destinasyon, mas sayon.**
