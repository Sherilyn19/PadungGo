# Proposed Architecture

**Status: design only; implementation not started.** The full product is a
location-to-location public transportation planner throughout Cebu City, Mandaue
City and Lapu-Lapu City, including intra-city, same-barangay and intercity trips.
The MVP uses a smaller verified interconnected subset. 01K, 23D, 20A and 03Q are
initial research leads, not architecture constants. A selectable location does
not guarantee a verified journey.

## Components and approved stack

```text
Browser: React + TypeScript + Vite + Tailwind CSS + shadcn/ui + MapLibre GL JS
    | HTTPS JSON; four endpoint-selection methods
    v
Python + Django + Django REST Framework
    |-- Location resolution and intended-area validation
    |-- Verified nearby-stop and pedestrian-access service
    |-- Directed network search: direct + at most one transfer in MVP
    |-- Fare service: versioned source-backed policies
    |-- Duration service: walking / waiting / riding; null when unknown
    |-- Deduplication and ranking: aim for 3–5 distinct alternatives
    |-- Public provenance and coverage limitations
    |-- Authenticated Django Admin: data import, review and evidence history
    v
Supabase PostgreSQL + PostGIS
    |
    +-- Licensed source/evidence records and reviewed directional network
```

Use one modular backend, not separate microservices. Frontend and backend may be
deployed independently where practical. MapLibre renders maps; it does not itself
supply licensed tiles, geocoding or pedestrian routing. Choose compliant providers
or curated verified pedestrian links before promising navigable walking guidance.
No live vehicle feed or AI model is required.

## Canonical data and API designs

[DATABASE_DESIGN.md](DATABASE_DESIGN.md) owns the schema: Area, Location, Stop,
Route, RoutePattern, PatternStop, RouteSegment, TransferConnection, FareRule,
DataSource, RouteEvidence and RecordEvidence. Stop occurrences and route direction
are distinct. Distances are meters, durations seconds and money integer centavos.

[API_DESIGN.md](API_DESIGN.md) owns exact shapes and error states:

- GET /api/v1/health
- GET /api/v1/locations
- GET /api/v1/routes
- GET /api/v1/routes/{id}
- POST /api/v1/journeys/plan

The same planner handles independent A→B and B→A queries. A separate return
endpoint is unnecessary. Public reads exclude unreviewed transport guidance.

## Journey pipeline

1. Normalize GPS, selected search result, map pin or predefined location for both
   endpoints to coordinates; distinguish geographic scope from dataset coverage.
2. Find eligible stop occurrences reachable through supported pedestrian access.
3. Search verified directional patterns in forward occurrence order.
4. Enumerate validated one-transfer connections; reject impossible line crossings.
5. Compute per-boarding fares using sourced policy and traveled route distance.
6. Propagate unknown walking/waiting/riding estimates and incomplete totals.
7. Deduplicate, rank supported comparisons and return at most five real options.
8. Run the same pipeline independently for requested return travel.

Search policy limits transfers; the graph/schema support additional transfers in
later releases. Spatial indexes and bounded candidate sets are sufficient initial
growth measures. Profile before adding caching, queues or distributed services.

## Trust, privacy and deployment

Keep Django secrets, Supabase credentials and private provider keys server-side.
The browser calls DRF rather than accessing administrative database tables.
Browser-visible map tokens must be designed for public use and restricted where
the provider supports it. Use least privilege, HTTPS, exact CORS origins, request
validation, throttling and auditable authorized administrative changes.

Do not store commuter GPS history; redact precise coordinates from logs. Keep
private reviewer details separate from public provenance. Retain third-party
attribution/permissions. Deployment requires tested migrations, environment
documentation, backups/restore checks, frontend build and backend health checks.
None of these operational controls is claimed to exist in the current starter.

## AI explanation layer

An open-weight model may explain a completed itinerary, source evidence and
uncertainty through a server-side Django service. The deterministic planner
remains authoritative for route discovery, direction validation, fare calculation
and verification status. Ollama is a private local runtime option; production
hosting is a later deployment decision. Kiro, ACP and MCP remain workshop or
development context unless a deliberate production integration is specified.

## Production deployment

The submitted MVP must run remotely rather than depend on the owner's computer:

```text
Browser
  → Deployed React frontend
  → Deployed Django/DRF API
      → Supabase PostgreSQL/PostGIS
      → Hosted open-weight model endpoint
```

The model endpoint is called server-side so credentials stay private. Ollama is
optional for local development only. The deployment provider, hosted model
provider, domains and budget remain decisions before implementation.
