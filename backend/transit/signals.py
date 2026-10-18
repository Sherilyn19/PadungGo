"""Invalidate the cached planner network whenever routable data changes."""
from django.db.models.signals import post_delete, post_save

from transit.planner.loader import clear_network_cache

_MODELS = (
    "DataSource", "Stop", "Route", "RoutePattern", "PatternStop", "RouteSegment",
    "TransferConnection", "FareRule", "RouteEvidence",
)


def _clear(**_kwargs):
    clear_network_cache()


def connect():
    from django.apps import apps

    for name in _MODELS:
        model = apps.get_model("transit", name)
        post_save.connect(_clear, sender=model, dispatch_uid=f"netcache-save-{name}")
        post_delete.connect(_clear, sender=model, dispatch_uid=f"netcache-del-{name}")
