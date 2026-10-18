"""Provenance and append-only evidence history (DataSource, *Evidence)."""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .enums import EvidenceStatus


class DataSource(models.Model):
    """Evidence and reuse provenance. Referenced (PROTECT) by routable records."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=300)
    publisher = models.CharField(max_length=300, blank=True)
    reference = models.CharField(
        max_length=1000,
        blank=True,
        help_text="Source URL or permitted-observation reference.",
    )
    published_at = models.DateField(null=True, blank=True)
    collected_at = models.DateTimeField(
        help_text="When this evidence was retrieved/observed by a reviewer."
    )
    license = models.CharField(
        max_length=300,
        blank=True,
        help_text="License or permission under which the data may be reused.",
    )
    limitations = models.TextField(
        blank=True,
        help_text="Known limitations: staleness, scope, embedded-provider terms.",
    )

    class Meta:
        ordering = ["title"]
        indexes = [models.Index(fields=["publisher"])]

    def __str__(self) -> str:
        return self.title


class RouteEvidence(models.Model):
    """Append-only pattern verification history. Never overwrite existing rows."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pattern = models.ForeignKey(
        "transit.RoutePattern", on_delete=models.PROTECT, related_name="evidence"
    )
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="+")
    observed_at = models.DateField(null=True, blank=True)
    reviewed_at = models.DateTimeField()
    reviewer = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=EvidenceStatus.choices)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-reviewed_at"]
        indexes = [models.Index(fields=["pattern", "-reviewed_at"])]

    def __str__(self) -> str:
        return f"{self.pattern} · {self.status} @ {self.reviewed_at:%Y-%m-%d}"


class RecordEvidence(models.Model):
    """Evidence history for non-pattern routable records.

    Exactly one typed target FK must be set (enforced by a DB CHECK constraint
    and in clean()). Direct typed FKs preserve referential integrity.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="+")
    observed_at = models.DateField(null=True, blank=True)
    reviewed_at = models.DateTimeField()
    reviewer = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=EvidenceStatus.choices)
    notes = models.TextField(blank=True)

    area = models.ForeignKey(
        "transit.Area", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    location = models.ForeignKey(
        "transit.Location", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    stop = models.ForeignKey(
        "transit.Stop", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    pattern_stop = models.ForeignKey(
        "transit.PatternStop", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    route_segment = models.ForeignKey(
        "transit.RouteSegment", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    transfer_connection = models.ForeignKey(
        "transit.TransferConnection", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )
    fare_rule = models.ForeignKey(
        "transit.FareRule", null=True, blank=True, on_delete=models.CASCADE, related_name="+"
    )

    _TARGET_FIELDS = (
        "area",
        "location",
        "stop",
        "pattern_stop",
        "route_segment",
        "transfer_connection",
        "fare_rule",
    )

    class Meta:
        ordering = ["-reviewed_at"]
        constraints = [
            models.CheckConstraint(
                name="recordevidence_exactly_one_target",
                condition=(
                    models.Q(area__isnull=False, location__isnull=True, stop__isnull=True,
                             pattern_stop__isnull=True, route_segment__isnull=True,
                             transfer_connection__isnull=True, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=False, stop__isnull=True,
                               pattern_stop__isnull=True, route_segment__isnull=True,
                               transfer_connection__isnull=True, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=True, stop__isnull=False,
                               pattern_stop__isnull=True, route_segment__isnull=True,
                               transfer_connection__isnull=True, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=True, stop__isnull=True,
                               pattern_stop__isnull=False, route_segment__isnull=True,
                               transfer_connection__isnull=True, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=True, stop__isnull=True,
                               pattern_stop__isnull=True, route_segment__isnull=False,
                               transfer_connection__isnull=True, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=True, stop__isnull=True,
                               pattern_stop__isnull=True, route_segment__isnull=True,
                               transfer_connection__isnull=False, fare_rule__isnull=True)
                    | models.Q(area__isnull=True, location__isnull=True, stop__isnull=True,
                               pattern_stop__isnull=True, route_segment__isnull=True,
                               transfer_connection__isnull=True, fare_rule__isnull=False)
                ),
            )
        ]

    def clean(self) -> None:
        set_targets = [f for f in self._TARGET_FIELDS if getattr(self, f + "_id")]
        if len(set_targets) != 1:
            raise ValidationError(
                "RecordEvidence must reference exactly one target record "
                f"(got {len(set_targets)}: {set_targets})."
            )

    def __str__(self) -> str:
        return f"RecordEvidence {self.status} @ {self.reviewed_at:%Y-%m-%d}"
