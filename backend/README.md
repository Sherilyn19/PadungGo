# Backend (to be scaffolded)

Planned: **Python 3.12 + Django 5.2 LTS + Django REST Framework + PostgreSQL**.

This starter contains documentation only; **no Django application has been generated**.

Example setup after repository initialization:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install "Django>=5.2,<5.3" djangorestframework django-cors-headers "psycopg[binary]" python-dotenv
.\.venv\Scripts\django-admin.exe startproject config .
.\.venv\Scripts\python.exe manage.py startapp transit
```

You must then configure Django settings, URL routes, models, DB connection and migrations. Do not treat this file as a working backend.
