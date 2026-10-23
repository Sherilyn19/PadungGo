"""Settings for the automated test suite (selected in pytest.ini).

Sets explicit test-only environment values, then loads the normal settings.
This replaces guessing "are we under test?" from the command line, which
could switch off production protections by accident.
"""
import os

os.environ.setdefault("PADUNGGO_TESTING", "True")
os.environ.setdefault("PADUNGGO_DB_ENGINE", "sqlite")  # no GDAL/PostGIS needed
os.environ.setdefault("DJANGO_DEBUG", "True")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-not-secret")
os.environ.setdefault("PADUNGGO_SQLITE_PATH", ":memory:")
# Never call the real Geoapify service from tests, even if a key is exported.
os.environ["GEOAPIFY_API_KEY"] = ""
# Never call a real AI provider from tests, even if a key is exported.
for _name in ("AI_BASE_URL", "AI_API_KEY", "AI_MODEL"):
    os.environ[_name] = ""

from config.settings import *  # noqa: E402,F401,F403
