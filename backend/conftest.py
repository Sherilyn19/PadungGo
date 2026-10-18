"""Pytest bootstrap: force lite (SQLite, no-GDAL) mode for the test suite."""
import os

os.environ.setdefault("PADUNGGO_DB_ENGINE", "sqlite")
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-key")
os.environ.setdefault("PADUNGGO_SQLITE_PATH", ":memory:")
