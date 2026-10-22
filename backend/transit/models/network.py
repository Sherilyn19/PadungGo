"""Directed network: Route, RoutePattern, PatternStop, RouteSegment, TransferConnection."""
from __future__ import annotations

import uuid

from django.core.validators import MinValueValidator
from django.db import models

from ..geocompat import linestring_field
from .enums import (
    EstimateBasis,
    PatternDirection,
    RecordStatus,
    StopStatus,
    VehicleClass,
)


class Route(models.Model):
    """Service identity. Route code is NOT globally unique by itself."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=20, help_text="e.g. 01K, 20A. Not globally unique.")
    name = models.CharField(max_length=200, blank=True)
    vehicle_class = models.CharField(max_length=20, choices=VehicleClass.choices)
    operator = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)
    service_availability = models.CharField(
        max_length=20,
        choices=[
            ("not_flagged", "Not flagged"),
            ("scarce", "Scarce"),
        ],
        default="not_flagged",
    )

    class Meta:
        ordering = ["code"]
        indexes = [models.Index(fields=["code"]), models.Index(fields=["active"])]

    def __str__(self) -> str:
        return f"{self.code} {self.name}".strip()


class RoutePattern(models.Model):
    """One directed, ordered variant of a route. A route may have many."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(Route, on_delete=models.PROTECT, related_name="patterns")
    variant_key = models.CharField(
        max_length=100, help_text="Distinguishes variants of the same route+direction."
    )
    direction = models.CharField(max_length=20, choices=PatternDirection.choices)
    signboard = models.CharField(max_length=200, blank=True)
    geometry = linestring_field()
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.CANDIDATE)
    verified_at = models.DateTimeField(null=True, blank=True)
    review_due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["route__code", "direction", "variant_key"]
        constraints = [
            models.UniqueConstraint(fields=["route", "variant_key"], name="routepattern_unique_route_variant"),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["direction"]),
            models.Index(fields=["route", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.route.code} [{self.direction}/{self.variant_key}]"


class PatternStop(models.Model):
    """Stop occurrence on a pattern. A loop may visit one physical stop repeatedly.

    (pattern, sequence) is unique; (pattern, stop) is intentionally NOT unique.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pattern = models.ForeignKey(RoutePattern, on_delete=models.CASCADE, related_name="pattern_stops")
    stop = models.ForeignKey("transit.Stop", on_delete=models.PROTECT, related_name="occurrences")
    sequence = models.PositiveIntegerField(help_text="0-based order along the directed pattern.")
    distance_along_m = models.PositiveIntegerField(
        default=0, help_text="Cumulative metres along the pattern; non-decreasing."
    )
    can_board = models.BooleanField(default=True)
    can_alight = models.BooleanField(default=True)

    class Meta:
        ordering = ["pattern", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["pattern", "sequence"], name="patternstop_unique_pattern_sequence"),
        ]
        indexes = [
            models.Index(fields=["pattern", "sequence"]),
            models.Index(fields=["stop", "pattern"]),
        ]

    def __str__(self) -> str:
        return f"{self.pattern} #{self.sequence} {self.stop.name}"


class RouteSegment(models.Model):
    """Consecutive stop occurrences and supported travel metrics along a pattern."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pattern = models.ForeignKey(RoutePattern, on_delete=models.CASCADE, related_name="segments")
    from_occurrence = models.ForeignKey(
        PatternStop, on_delete=models.CASCADE, related_name="segments_from"
    )
    to_occurrence = models.ForeignKey(
        PatternStop, on_delete=models.CASCADE, related_name="segments_to"
    )
    distance_m = models.PositiveIntegerField(
        help_text="Travelled route distance along the pattern (metres)."
    )
    geometry = linestring_field()
    # Supported ride time; NULL when unknown (never assume 0).
    riding_seconds = models.PositiveIntegerField(null=True, blank=True)
    estimate_basis = models.CharField(
        max_length=30, choices=EstimateBasis.choices, blank=True
    )
    source = models.ForeignKey(
        "transit.DataSource", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["pattern", "from_occurrence__sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["pattern", "from_occurrence", "to_occurrence"],
                name="routesegment_unique_pattern_from_to",
            ),
        ]
        indexes = [models.Index(fields=["pattern"])]

    def __str__(self) -> str:
        return f"{self.pattern} seg {self.from_occurrence.sequence}->{self.to_occurrence.sequence}"


class TransferConnection(models.Model):
    """Directed, validated pedestrian transfer. Reverse is NOT assumed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_stop = models.ForeignKey(
        "transit.Stop", on_delete=models.PROTECT, related_name="transfers_from"
    )
    to_stop = models.ForeignKey(
        "transit.Stop", on_delete=models.PROTECT, related_name="transfers_to"
    )
    pedestrian_geometry = linestring_field()
    distance_m = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Walking distance (metres); 0 for same-stop reboarding; NULL if unknown.",
    )
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    restrictions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.CANDIDATE)
    verified_at = models.DateTimeField(null=True, blank=True)
    source = models.ForeignKey(
        "transit.DataSource", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        ordering = ["from_stop", "to_stop"]
        # from_stop == to_stop is allowed: explicit same-stop reboarding
        # (docs/DATABASE_DESIGN.md "including same-stop reboarding").
        constraints = [
            models.UniqueConstraint(fields=["from_stop", "to_stop"], name="transfer_unique_from_to"),
        ]
        indexes = [models.Index(fields=["from_stop", "status"]), models.Index(fields=["status"])]

    def __str__(self) -> str:
        return f"{self.from_stop.name} -> {self.to_stop.name}"
