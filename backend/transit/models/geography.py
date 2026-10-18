"""Geographic context: Area, Location, Stop."""
from __future__ import annotations

import uuid

from django.db import models

from ..geocompat import point_field
from .enums import AreaKind, LocationKind, RecordStatus, StopStatus


class Area(models.Model):
    """Hierarchical geographic context (city / barangay / community)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=AreaKind.choices)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="children"
    )
    # Boundary geometry needs licensed evidence; omitted here until available.
    source = models.ForeignKey(
        "transit.DataSource", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["name", "kind", "parent"], name="area_unique_name_kind_parent"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.kind})"


class Location(models.Model):
    """Searchable curated place / landmark / terminal. Not every commuter point."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    kind = models.CharField(max_length=20, choices=LocationKind.choices, default=LocationKind.PLACE)
    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.PROTECT, related_name="locations"
    )
    # WGS84 point. Stored as PointField (PostGIS) or {"lat","lon"} JSON (lite).
    point = point_field()
    latitude = models.FloatField(help_text="WGS84 latitude [-90, 90].")
    longitude = models.FloatField(help_text="WGS84 longitude [-180, 180].")
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.CANDIDATE)
    verified_at = models.DateTimeField(null=True, blank=True)
    source = models.ForeignKey(
        "transit.DataSource", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["name"]), models.Index(fields=["status"])]

    def __str__(self) -> str:
        return self.name


class Stop(models.Model):
    """Physical eligible boarding/alighting point; distinct from a general place."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    area = models.ForeignKey(
        Area, null=True, blank=True, on_delete=models.PROTECT, related_name="stops"
    )
    point = point_field()
    latitude = models.FloatField(help_text="WGS84 latitude [-90, 90].")
    longitude = models.FloatField(help_text="WGS84 longitude [-180, 180].")
    can_board = models.BooleanField(default=True, help_text="Boarding allowed here by default.")
    can_alight = models.BooleanField(default=True, help_text="Alighting allowed here by default.")
    status = models.CharField(max_length=20, choices=StopStatus.choices, default=StopStatus.CANDIDATE)
    verified_at = models.DateTimeField(null=True, blank=True)
    source = models.ForeignKey(
        "transit.DataSource", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["status"])]

    def __str__(self) -> str:
        return self.name
