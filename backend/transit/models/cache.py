"""Shared marker that tells every server process when route data has changed."""
from django.db import models


class NetworkDataVersion(models.Model):
    """A single row whose counter goes up whenever routable data changes.

    Each web worker keeps its own in-memory copy of the planner network. A GTFS
    import or an admin edit happens in only one process (sometimes a separate
    `manage.py` command), so the other workers cannot see their copy is out of
    date. Before using its copy, a worker compares this shared counter with the
    one it loaded, and reloads if they differ.
    """

    SINGLETON_ID = 1

    id = models.PositiveSmallIntegerField(primary_key=True, default=SINGLETON_ID)
    version = models.PositiveBigIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "network data version"

    def __str__(self) -> str:
        return f"Network data version {self.version}"
