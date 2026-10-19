"""Invalidate the cached planner network whenever routable data changes.

Covers saves and deletes made through the ORM, for example in Django Admin.
Bulk writes (bulk_create, QuerySet.update) do not send these signals, so the
GTFS importer invalidates explicitly once it has finished.
"""
from django.db.models.signals import post_delete, post_save

from transit.planner.loader import invalidate_network_cache

_MODELS = (
    "DataSource", "Stop", "Route", "RoutePattern", "PatternStop", "RouteSegment",
    "TransferConnection", "FareRule", "RouteEvidence",
)


def _invalidate(**_kwargs):
    invalidate_network_cache()


def connect():
    from django.apps import apps

    for name in _MODELS:
        model = apps.get_model("transit", name)
        post_save.connect(_invalidate, sender=model, dispatch_uid=f"netcache-save-{name}")
        post_delete.connect(_invalidate, sender=model, dispatch_uid=f"netcache-del-{name}")
