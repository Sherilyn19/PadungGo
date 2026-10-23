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
No live vehicle feed is required. The only AI is the optional, on-request
"Explain this trip" text described below; planning never depends on it.

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

An open-weight model can restate one finished itinerary in plain English
("Explain this trip"). The deterministic planner stays authoritative for routes,
stops, transfers, fares, timing, scarcity and verification status; the model only
rewords facts the planner already produced. It is optional and on request: the
planner, the map and every itinerary work when the AI is unavailable.

```text
Browser (Trip details, "Explain this trip")
  → POST /api/v1/journeys/explain   (search inputs + opaque ride IDs only)
      → Django plans again and finds that exact trip in the planner output
      → transit/ai/trip_facts.py   minimal facts (no coordinates, no place names)
      → transit/ai/provider.py     OpenAI-compatible call, timeout, daily cap
          → GroqCloud: openai/gpt-oss-20b (Apache 2.0 open weights)
      → transit/ai/output_checks.py accepts the text only if it keeps the facts
```

Design decisions:

- **No client-supplied facts.** The browser sends only the search it already made
  and the IDs of the chosen rides. The server reconstructs the trip, so a client
  cannot make the AI repeat an invented route, stop or fare. Extra fields are
  rejected (400) and IDs that match no planned trip return 404.
- **Minimum data to the provider.** Route codes and names, stop names, transfer
  order, scarce flags, known ride minutes, and the fare only if the planner has a
  complete one. No GPS coordinates, typed place names, IDs or user identifiers.
  Coordinates reach Django (as they already do for planning) but are neither
  forwarded nor logged.
- **Checked output.** The text is shown only if it names every route code in
  order and every stop, repeats the historic / scarce / unknown-fare /
  unknown-wait warnings, and adds no route code, price, time, distance, frequency
  or "running now" claim. Failing answers get one retry, then "unavailable".
  The warnings are also returned separately, written by the server, so they never
  depend on the model. These checks are a safety net, not proof that every
  sentence is true; the UI says so.
- **Failure isolation.** Timeout, rate limit, quota, bad reply or missing
  configuration all return HTTP 200 with `status: "unavailable"` and a plain
  message. Per-visitor throttle (`DRF_EXPLAIN_THROTTLE`, default 6/min), a shared
  daily provider cap, and a per-trip answer cache keep usage inside the free quota.

Ollama is not used. Kiro, ACP and MCP are development tools, not part of the
product.

## Production deployment

The submitted MVP must run remotely rather than depend on the owner's computer:

```text
Browser
  → Deployed React frontend
  → Deployed Django/DRF API
      → Supabase PostgreSQL/PostGIS
      → Hosted open-weight model endpoint
```

The model endpoint is called server-side so credentials stay private. The hosted
provider is GroqCloud with `openai/gpt-oss-20b`; its key is a Render environment
variable (`AI_API_KEY`), never part of the repository or the frontend bundle.
