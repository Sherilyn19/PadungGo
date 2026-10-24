# PadungGo backend

Django and Django REST Framework provide the public API, deterministic journey planner, and authenticated data administration. Python 3.12 is used in production. SQLite supports local development and tests; PostgreSQL/PostGIS supports deployment.

- [Local setup and checks](../docs/REPOSITORY_SETUP.md)
- [API behavior](../docs/API_DESIGN.md)
- [Architecture](../docs/ARCHITECTURE.md) and [database](../docs/DATABASE_DESIGN.md)
- [Deployment and environment settings](../docs/DEPLOYMENT.md)
- [AI explanations](../docs/AI_EXPLANATIONS.md)

## Import a transport feed

The repository does not bundle a feed or establish reuse permission for the historical Cebu archive. Check [data rights](../docs/DATA_SOURCES.md) first. Use an authorized General Transit Feed Specification (GTFS) ZIP with routes, trips, stops, stop times, and shapes. From this directory, using the local virtual environment:

```powershell
.\.venv\Scripts\python.exe manage.py import_gtfs "path/to/feed.zip" --title "Source and version" --reference "https://source.example/feed" --publisher "Publisher" --license "Verified source terms"
```

Replace the example metadata with actual evidence. Run `manage.py import_gtfs --help` for supported flags, including publication date, limitations, vehicle class, and `--no-same-stop-transfers`. This command writes data; it has no dry-run flag. The authenticated Admin also supports feed uploads.

Imports produce documented records, not verified service. Default same-stop transfers are inferred from shared stops, not field-confirmed pedestrian access. Archived schedules do not establish today's timetable. Different source titles can create duplicate routes; reconcile availability decisions and identity before re-importing. Route codes are not unique keys.

Admin tools also support named-place imports from OpenStreetMap, stop boarding/alighting changes, and previewing a start extension from an OpenStreetMap route. Preview and review the exact records and provenance before applying changes. These tools do not automatically verify a route.

## Source map

`transit/api/` validates requests and exposes endpoints; `transit/planner/` loads and searches the network; `transit/places/` handles optional place services; `transit/ai/` explains selected trips. Models, migrations, Admin code, import commands, and tests live under `transit/`. See the [architecture guide](../docs/ARCHITECTURE.md) for interactions.
