"""Controlled vocabularies. Lowercase string values stored everywhere."""
from __future__ import annotations

from django.db import models


class RecordStatus(models.TextChoices):
    """Canonical review projection used across routable records.

    Only VERIFIED is eligible for trusted journey search by default.
    """

    CANDIDATE = "candidate", "Candidate"
    DOCUMENTED = "documented", "Documented"
    VERIFIED = "verified", "Verified"
    NEEDS_REVIEW = "needs_review", "Needs review"


class EvidenceStatus(models.TextChoices):
    """Outcome recorded on an append-only evidence row."""

    CANDIDATE = "candidate", "Candidate"
    DOCUMENTED = "documented", "Documented"
    VERIFIED = "verified", "Verified"
    NEEDS_REVIEW = "needs_review", "Needs review"
    REJECTED = "rejected", "Rejected"


class AreaKind(models.TextChoices):
    CITY = "city", "City"
    BARANGAY = "barangay", "Barangay"
    COMMUNITY = "community", "Community"


class LocationKind(models.TextChoices):
    LANDMARK = "landmark", "Landmark"
    TERMINAL = "terminal", "Terminal"
    MALL = "mall", "Mall"
    TRANSPORT_HUB = "transport_hub", "Transport hub"
    PLACE = "place", "Place"


class StopStatus(models.TextChoices):
    CANDIDATE = "candidate", "Candidate"
    DOCUMENTED = "documented", "Documented"
    VERIFIED = "verified", "Verified"
    NEEDS_REVIEW = "needs_review", "Needs review"
    RETIRED = "retired", "Retired"


class VehicleClass(models.TextChoices):
    """Controlled field rather than a catalog table (per DATABASE_DESIGN)."""

    JEEPNEY = "jeepney", "Jeepney"
    BUS = "bus", "Bus"
    MODERN_PUV = "modern_puv", "Modern PUV"
    # A route served by both traditional and modern units. No fare rule can
    # target it, so its fare stays Unknown instead of showing one vehicle's price.
    MIXED = "mixed", "Mixed fleet (traditional and modern)"


class PatternDirection(models.TextChoices):
    OUTBOUND = "outbound", "Outbound"
    INBOUND = "inbound", "Inbound"
    LOOP = "loop", "Loop"
    # Source does not state a direction; the pattern's stop order is still
    # directed and enforced. Shown honestly rather than guessed.
    UNSPECIFIED = "unspecified", "Unspecified"


class EstimateBasis(models.TextChoices):
    """How a supported duration/distance estimate was derived. Never 'live'."""

    SOURCED_OBSERVATION = "sourced_observation", "Sourced observation"
    SCHEDULE = "schedule", "Published schedule"
    DISTANCE_SPEED_ASSUMPTION = "distance_speed_assumption", "Distance + documented speed"
    STRAIGHT_LINE_APPROX = "straight_line_approx", "Straight-line approximation"


class FarePolicyKind(models.TextChoices):
    FLAT = "flat", "Flat fare"
    DISTANCE_BAND = "distance_band", "Distance-banded fare"


class PassengerCategory(models.TextChoices):
    REGULAR = "regular", "Regular"
    STUDENT = "student", "Student"
    SENIOR = "senior", "Senior citizen"
    PWD = "pwd", "Person with disability"
