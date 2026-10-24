# PadungGo frontend

React, TypeScript, Vite, Tailwind CSS, and MapLibre provide the commuter interface. The frontend calls the Django API; it does not connect directly to the database. Map tiles use OpenFreeMap with OpenStreetMap attribution.

- [Run locally and test](../docs/REPOSITORY_SETUP.md)
- [Commuter guide](../docs/USER_FLOW.md)
- [API behavior](../docs/API_DESIGN.md)
- [Deployment](../docs/DEPLOYMENT.md)

The interface supports place search, device location, map pins, direct/one-transfer journeys, independent return search, fare-estimate choices, scarcity notices, and optional AI explanations. It requests up to 50 alternatives and reveals eight at a time. Ride lines use stored geometry; dashed walking connections are not verified pedestrian paths.

The welcome screen is timed at five seconds per page mount, independently of API readiness. Waiting times and complete trip durations remain unknown. The fare selector affects displayed estimates, not the facts supplied to AI.

`VITE_API_BASE_URL` is embedded in the public build. Never put credentials in `VITE_*` variables. Frontend changes are checked with Vitest and the TypeScript/Vite production build; a passing build is not a browser accessibility or end-to-end test.
