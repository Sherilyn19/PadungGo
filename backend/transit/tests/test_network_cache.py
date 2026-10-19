"""Regression tests: the planner network cache must not serve stale data.

Each web worker keeps its own cached copy. Before the fix, an import or edit
in one process left the other workers (and every worker, after a
`manage.py import_gtfs`) serving outdated journeys for up to five minutes.
"""
from __future__ import annotations

import pytest
from django.db.models import F

from transit.models import NetworkDataVersion, Stop
from transit.planner import loader
from transit.tests.db_fixtures import build_verified_network

pytestmark = pytest.mark.django_db


def _stop_count(network) -> int:
    return len(network.stops)


def _add_stop_without_signals(name: str) -> None:
    # bulk_create sends no post_save signal, just like the GTFS importer's writes.
    Stop.objects.bulk_create([Stop(name=name, latitude=10.3, longitude=123.95, status="verified")])


def test_cached_copy_is_reused_while_data_is_unchanged():
    build_verified_network()
    first = loader.load_network()
    assert loader.load_network() is first


def test_change_from_another_process_is_picked_up():
    build_verified_network()
    before = _stop_count(loader.load_network())

    # Simulate another worker or a `manage.py import_gtfs` process: it changes
    # the data and bumps the shared version, but cannot clear OUR in-memory copy.
    _add_stop_without_signals("Added elsewhere")
    NetworkDataVersion.objects.filter(pk=NetworkDataVersion.SINGLETON_ID).update(
        version=F("version") + 1
    )

    assert _stop_count(loader.load_network()) == before + 1


def test_invalidate_bumps_shared_version():
    loader.invalidate_network_cache()
    v1 = NetworkDataVersion.objects.get().version
    loader.invalidate_network_cache()
    assert NetworkDataVersion.objects.get().version == v1 + 1


def test_admin_style_save_invalidates_via_signal():
    build_verified_network()
    before = _stop_count(loader.load_network())
    Stop.objects.create(name="Saved in admin", latitude=10.3, longitude=123.95, status="verified")
    assert _stop_count(loader.load_network()) == before + 1
