"""Regression tests for production settings and GTFS upload hardening."""
from __future__ import annotations

import io
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from transit.importers.gtfs import GTFSImportError, ImportOptions, import_gtfs
from transit.tests.test_gtfs_import import _feed

BACKEND_DIR = Path(__file__).resolve().parents[2]
IMPORT_URL = "/admin/transit/datasource/import-gtfs/"


# --- Production settings ---------------------------------------------------


def _import_settings(env_overrides: dict, *argv: str) -> subprocess.CompletedProcess:
    """Import config.settings in a clean process with only the given env."""
    env = {"PATH": os.environ.get("PATH", ""), "PADUNGGO_DB_ENGINE": "sqlite", **env_overrides}
    code = (
        "import sys; sys.path.insert(0, '.'); import config.settings as s; "
        "print(s.SESSION_COOKIE_SECURE, s.CSRF_COOKIE_SECURE)"
    )
    return subprocess.run(
        [sys.executable, "-c", code, *argv], cwd=BACKEND_DIR, env=env,
        capture_output=True, text=True, timeout=60,
    )


def test_production_without_secret_refuses_to_start_even_if_argv_mentions_pytest():
    # Regression: "pytest" anywhere on the command line used to enable the
    # insecure fallback key and skip the HTTPS/secure-cookie settings.
    result = _import_settings({"DJANGO_DEBUG": "False"}, "pytest", "test")
    assert result.returncode != 0
    assert "DJANGO_SECRET_KEY must be set" in result.stderr


def test_production_rejects_the_dev_only_key():
    result = _import_settings({"DJANGO_DEBUG": "False",
                               "DJANGO_SECRET_KEY": "dev-insecure-key-change-me"})
    assert result.returncode != 0


def test_production_enables_secure_cookies():
    result = _import_settings({"DJANGO_DEBUG": "False", "DJANGO_SECRET_KEY": "x" * 50})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "True True"


# --- GTFS upload -----------------------------------------------------------


@pytest.mark.django_db
def test_oversized_upload_rejected_before_body_is_read(admin_client, settings):
    settings.GTFS_UPLOAD_MAX_BYTES = 10
    # Declared length well above limit + form allowance; body never parsed.
    resp = admin_client.generic("POST", IMPORT_URL, data=b"x",
                                content_type="multipart/form-data; boundary=x",
                                CONTENT_LENGTH=str(5 * 1024 * 1024))
    assert resp.status_code == 413


@pytest.mark.django_db
def test_non_zip_extension_rejected(admin_client):
    resp = admin_client.post(IMPORT_URL, {
        "feed": SimpleUploadedFile("feed.txt", _feed().getvalue()),
        "title": "Bad extension", "vehicle_class": "jeepney",
    })
    assert resp.status_code == 200
    assert b"File extension" in resp.content
    assert b"Imported" not in resp.content


@pytest.mark.django_db
def test_renamed_non_zip_rejected(admin_client):
    resp = admin_client.post(IMPORT_URL, {
        "feed": SimpleUploadedFile("feed.zip", b"definitely not a zip"),
        "title": "Fake zip", "vehicle_class": "jeepney",
    })
    assert b"not a valid zip archive" in resp.content


@pytest.mark.django_db
def test_feed_too_large_once_unzipped_rejected(settings):
    settings.GTFS_MAX_UNCOMPRESSED_BYTES = 100  # the test feed is bigger than this
    with pytest.raises(GTFSImportError, match="once unzipped"):
        import_gtfs(_feed(), ImportOptions(source_title="Bomb"))


@pytest.mark.django_db
def test_archive_with_too_many_members_rejected():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(201):
            zf.writestr(f"f{i}.txt", "")
    buf.seek(0)
    with pytest.raises(GTFSImportError, match="too many files"):
        import_gtfs(buf, ImportOptions(source_title="Many"))
