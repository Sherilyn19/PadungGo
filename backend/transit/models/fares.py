"""Versioned, source-backed fare policy. No fare constants in code."""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .enums import FarePolicyKind, PassengerCategory, RecordStatus, VehicleClass


class FareRule(models.Model):
    """A versioned fare policy with a source and effective date range.

    Applicability is resolved most-specific-first: pattern > route > vehicle
    class. The `policy` JSON holds the structured bands/increments/rounding; it
    is validated structurally (see clean()) but never seeded with invented
    amounts. Money is integer centavos.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle_class = models.CharField(max_length=20, choices=VehicleClass.choices)
    route = models.ForeignKey(
        "transit.Route", null=True, blank=True, on_delete=models.PROTECT, related_name="fare_rules"
    )
    pattern = models.ForeignKey(
        "transit.RoutePattern", null=True, blank=True, on_delete=models.PROTECT, related_name="fare_rules"
    )
    passenger_category = models.CharField(
        max_length=20, choices=PassengerCategory.choices, default=PassengerCategory.REGULAR
    )
    currency = models.CharField(max_length=3, default="PHP")
    kind = models.CharField(max_length=20, choices=FarePolicyKind.choices)
    policy = models.JSONField(
        help_text=(
            "Structured policy. flat: {'amount_centavos': int}. "
            "distance_band: {'base_centavos': int, 'base_distance_m': int, "
            "'increment_centavos': int, 'increment_distance_m': int, "
            "'rounding_centavos': int (optional)}."
        )
    )
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.CANDIDATE)
    source = models.ForeignKey(
        "transit.DataSource", on_delete=models.PROTECT, related_name="fare_rules"
    )

    class Meta:
        ordering = ["vehicle_class", "-valid_from"]
        indexes = [
            models.Index(fields=["vehicle_class", "status"]),
            models.Index(fields=["route", "status"]),
            models.Index(fields=["pattern", "status"]),
            models.Index(fields=["valid_from", "valid_until"]),
        ]
        constraints = [
            models.CheckConstraint(
                name="farerule_valid_date_range",
                condition=models.Q(valid_until__isnull=True)
                | models.Q(valid_until__gte=models.F("valid_from")),
            ),
            # A rule may target a pattern or a route, not both at once.
            models.CheckConstraint(
                name="farerule_not_both_route_and_pattern",
                condition=~models.Q(route__isnull=False, pattern__isnull=False),
            ),
        ]

    @property
    def specificity(self) -> int:
        """Higher is more specific: pattern(2) > route(1) > vehicle class(0)."""
        if self.pattern_id:
            return 2
        if self.route_id:
            return 1
        return 0

    def clean(self) -> None:
        validate_fare_policy(self.kind, self.policy)

    def __str__(self) -> str:
        return f"Fare[{self.vehicle_class}/{self.passenger_category}] from {self.valid_from}"


def validate_fare_policy(kind: str, policy: object) -> None:
    """Validate policy JSON structure. Raises ValidationError on problems.

    Shared with the fare service so the planner and admin apply one definition.
    """
    if not isinstance(policy, dict):
        raise ValidationError("Fare policy must be a JSON object.")

    def _nonneg_int(key: str, required: bool = True) -> None:
        if key not in policy:
            if required:
                raise ValidationError(f"Fare policy missing required key '{key}'.")
            return
        value = policy[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValidationError(f"Fare policy '{key}' must be a non-negative integer.")

    if kind == FarePolicyKind.FLAT:
        _nonneg_int("amount_centavos")
    elif kind == FarePolicyKind.DISTANCE_BAND:
        _nonneg_int("base_centavos")
        _nonneg_int("base_distance_m")
        _nonneg_int("increment_centavos")
        _nonneg_int("increment_distance_m")
        if policy.get("increment_distance_m", 0) == 0:
            raise ValidationError("distance_band 'increment_distance_m' must be > 0.")
        _nonneg_int("rounding_centavos", required=False)
    else:
        raise ValidationError(f"Unknown fare policy kind '{kind}'.")
