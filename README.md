# PadungGo

**Asa ka padung? PadungGo!**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/Sherilyn19/PadungGo/actions/workflows/ci.yml/badge.svg)](https://github.com/Sherilyn19/PadungGo/actions/workflows/ci.yml)
[![Contributions welcome](https://img.shields.io/badge/Contributions-welcome-green.svg)](CONTRIBUTING.md)

PadungGo helps commuters explore public-transport journeys in Metro Cebu: what to ride, where to board, where to get off, and how to return.

**[Try PadungGo](https://padung-go.app)** · [Commuter guide](docs/USER_FLOW.md) · [Local setup](docs/REPOSITORY_SETUP.md) · [Documentation](docs/README.md)

## What the current version does

- Choose an origin and destination by place search, device location, or map pin.
- Find direct journeys and journeys with one transfer, with numbered instructions and mapped ride lines.
- Request up to 50 alternatives and reveal results eight at a time when available.
- Calculate a return journey independently, since routes may differ by direction.
- Show approximate fare-guide estimates by passenger category and selected vehicle type, or leave unsupported fares unknown.
- Flag reported scarce services and place journeys using them after other results.
- Explain a selected trip in plain English through the optional **Explain this trip** AI button.

The intended coverage is Cebu City, Mandaue City, and Lapu-Lapu City. Actual results depend on the stored network; selecting a place does not establish that a suitable service exists.

## Before you travel

**The route network is based on the historic Cebu DOTC transport archive (2014–2017), with selected later reports and map corrections. It is not a field-verified current network.** Confirm the route, boarding point, vehicle, and fare locally before travelling.

- A suggested route may have changed or may no longer operate. “Scarce” reflects reports, not measured frequency; an unflagged service is not confirmed frequent.
- Waiting times and complete journey times are unknown. Archived ride durations are not live predictions.
- Walking lines are straight connections, not checked pedestrian paths or safe-crossing instructions.
- Fare estimates use recorded ride distances and assumptions. Vehicle applicability and fractional-distance charging remain uncertain. Ask the driver; see the [fare evidence and limitations](docs/FARE_GUIDE_2026-09-28.md).
- Searches support at most one transfer and do not enumerate every possible journey. There is no exact city-boundary check in the planner.
- AI text can be wrong. It restates the planner’s trip and does not verify service. It does not use the passenger and vehicle choices used for the on-screen fare estimate.
- The hosted API may need time to wake after inactivity. Provider failures can make address labels or AI explanations unavailable.

## Run and contribute

Follow the [local setup guide](docs/REPOSITORY_SETUP.md) for Windows or macOS/Linux. A fresh database contains no routes. The repository does not bundle the historical feed; obtain data with suitable permissions before importing it.

Contributions to route evidence, accessibility, documentation, tests, and code are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md), the [data verification guide](docs/DATA_VERIFICATION.md), and the [security notes](docs/SECURITY.md).

## Technology and structure

The frontend uses React, TypeScript, Vite, Tailwind CSS, and MapLibre. The backend uses Python, Django, and Django REST Framework. Production uses PostgreSQL with PostGIS; local development and automated tests can use SQLite.

| Directory | Contents |
|---|---|
| [frontend](frontend/README.md) | Commuter interface and frontend tests |
| [backend](backend/README.md) | API, planner, data administration, imports, and backend tests |
| [data](data/README.md) | Data contribution guidance; no bundled transport feed |
| [docs](docs/README.md) | Product, architecture, API, sources, operations, and review records |
| [.github](.github) | Automated checks and contribution templates |

The configured deployment uses Vercel for the frontend, Render for the API, and Supabase PostgreSQL/PostGIS. See [deployment](docs/DEPLOYMENT.md) for configuration and operating limits. The [implementation review](docs/IMPLEMENTATION_REVIEW.md) records what was actually checked; a badge is not a guarantee of current service or data quality.

## AI assistance

“Explain this trip” uses `openai/gpt-oss-20b`, an open-weight model hosted by GroqCloud. The backend recomputes the selected itinerary and supplies limited trip facts, checks the returned text, and adds its own notices. The API key stays on the server. Planning does not depend on the AI provider.

See [AI behavior, privacy, and limits](docs/AI_EXPLANATIONS.md). The model has its own [Apache 2.0 license and model card](https://huggingface.co/openai/gpt-oss-20b); hosting has separate [provider terms and documentation](https://console.groq.com/docs/model/openai/gpt-oss-20b).

## License and data rights

Original PadungGo code and documentation are licensed under the [MIT License](LICENSE). This does not grant rights to third-party transport data, maps, fonts, icons, or hosted services.

**Reuse and redistribution permissions for the historical Cebu DOTC feed have not been established in this review.** Public access to an archive is not a license. OpenStreetMap data has separate attribution and database-license obligations. See the [source and rights register](docs/DATA_SOURCES.md) before reusing or publishing data.
