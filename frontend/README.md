# Frontend (to be scaffolded)

Planned: **React + TypeScript + Vite**, Tailwind CSS, shadcn/ui, and MapLibre GL JS.

This starter contains documentation only; **no React application has been generated**.

Once authorized to proceed, from the repository root:

```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

If Vite refuses to scaffold into an existing directory because this README exists, first temporarily move this README elsewhere (or create the Vite app in a temporary directory and merge it). Do not delete project notes without saving them.

Keep browser-visible environment variables non-secret. Never place database passwords or private API credentials in `VITE_*` values.

## Planned product behavior

Both endpoints support appropriate GPS, search, map and predefined selections within and across Cebu City, Mandaue City and Lapu-Lapu City. Explain the smaller verified MVP coverage; a selectable point does not guarantee a journey. Aim for 3–5 distinct valid alternatives and independently query return travel through [the canonical API](../docs/API_DESIGN.md). No interface is implemented yet.


The planned results view includes a clearly labeled AI explanation panel grounded
in the selected deterministic itinerary, public sources and uncertainty warnings.
It must not present model-generated text as independent route verification.


The submitted frontend must be deployed and reachable remotely. It must call the
deployed Django API rather than a localhost service; the AI explanation panel must
work through the deployed backend.
