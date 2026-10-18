# PadungGo Frontend

React + TypeScript + Vite, Tailwind CSS, MapLibre GL JS with OpenFreeMap tiles
(OpenStreetMap data, no API key). It calls the Django API; it never talks to the
database directly.

## Run locally (Windows PowerShell)

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local   # set VITE_API_BASE_URL if not using a local backend
npm run dev                         # http://localhost:5173
npm test                            # unit tests
npm run build                       # production build into dist/
```

`VITE_API_BASE_URL` is public (it ends up in the browser bundle). Never put
secrets in `VITE_*` variables.

## Deploy to Vercel

- Root Directory: `frontend` (Vite is auto-detected; build `npm run build`, output `dist`).
- Environment variable: `VITE_API_BASE_URL=https://padunggo-api.onrender.com/api/v1`.
- Then set `FRONTEND_ORIGIN` on the Render backend to the Vercel URL
  (for example `https://padunggo.vercel.app`) so the browser is allowed to call the API.

## What the UI shows

- Start/destination by search, device location, or tapping the map.
- Up to five options, direct or with one transfer; independent return trip.
- Ride lines follow the imported route shapes. Walk legs are dashed straight
  lines, labelled as not verified walking paths.
- Unknown fares, waits and walking times are shown as "Unknown", never zero.
- Historic GTFS results are labelled "not field-verified".
