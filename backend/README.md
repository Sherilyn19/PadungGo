# Backend (to be scaffolded)

Planned: **Python 3.12 + Django 5.2 LTS + Django REST Framework + Supabase PostgreSQL + PostGIS**.

This starter contains documentation only; **no Django application has been generated**.

Example setup after design approval, from the backend directory. Runtime versions below are proposed; these commands have not been tested in this documentation-only starter:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "Django>=5.2,<5.3" djangorestframework django-cors-headers "psycopg[binary]" python-dotenv
.\.venv\Scripts\django-admin.exe startproject config .
.\.venv\Scripts\python.exe manage.py startapp transit
```

You must then configure Django settings, URL routes, models, DB connection and migrations. Do not treat this file as a working backend.


## Planned AI service

Add an isolated Django service that calls an open-weight model through a private
runtime through the hosted inference API during development and production. The model may explain selected
itineraries and warnings, but it must not write route, fare or evidence records.


## Deployment requirement

The backend must run in a deployed environment for the submitted MVP. A hosted
open-weight inference endpoint is the production AI option; Ollama is for optional
private development only. Keep model/API credentials server-side and configure
health checks, HTTPS, allowed hosts and restricted CORS.
