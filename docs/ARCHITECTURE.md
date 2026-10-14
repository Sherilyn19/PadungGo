# Proposed Architecture

**Status: design only — implementation not started.**

```text
Browser (React + TypeScript + MapLibre)
    | HTTPS JSON API
    v
Django + Django REST Framework
    |-- Location and nearby-stop service
    |-- Direction-aware route finder: direct + one transfer
    |-- Alternative ranking: cheapest / duration / fewest transfers
    |-- Fare calculator (versioned sourced rules)
    |-- Duration service: walking / waiting (when known) / riding
    |-- Route provenance and verification filtering
    |-- Django Admin: curated route and source records
    |
    v
PostgreSQL (Supabase; PostGIS when appropriate)
```

## Proposed core database entities

1. `Route`: route identifier, operator, vehicle type, assigned fare rule.
2. `RoutePattern`: one travel direction / variant, geometry, verified status and date.
3. `Stop`: geographic point, name, city, boarding/alighting rules.
4. `PatternStop`: ordered stops for a directional route pattern; cumulative distance.
5. `RouteSegment`: successive stops, length, optional observed travel duration.
6. `FareRule`: vehicle/fare class, effective date, distance bands/rounding rules, authoritative source.
7. `DataSource`: publisher, URL, publication/retrieval dates, license/permissions.
8. `RouteEvidence`: verification record, source, observer/reviewer, notes and observed date.

Route patterns must distinguish directions and variants even if route codes match. Use integer centavos for money, and treat fare brackets and rounding as policy-derived rules.

## Backend routes (planned)

- `GET /api/health/`
- `GET /api/locations/`
- `GET /api/routes/`
- `GET /api/routes/{id}/`
- `POST /api/journeys/plan/`

The same planning endpoint handles A→B and B→A; each returns **all available valid alternatives up to a reasonable cap**, independently ranked.

## Journey planner (MVP)

1. Normalize GPS/map/search/dropdown selections to coordinates.
2. Find nearby valid boarding and final alighting points; account for pedestrian access.
3. Search verified direct route patterns in forward stop order.
4. Search verified one-transfer combinations with safe walking transfers.
5. Calculate separate ride fares; use actual fare rounding and discount policy where confirmed.
6. Estimate pedestrian/vehicle durations and only add waiting if a verified timetable/headway supports it.
7. Rank, deduplicate, return up to several valid journeys; never fabricate missing options.
8. Repeat the search with origin/destination reversed for a return request.

## Privacy and security

- No commuter registration or route history database for the MVP.
- GPS requires explicit browser permission; allow manual alternative.
- Protect database credentials and Django secret keys on the server.
- Scope CORS to deployed frontend origins; validate input coordinates and rate-limit costly requests.
- Don't use unlicensed commercial route data or unrestricted geocoding/tiles without provider permission.
