"""DRF serializers for request validation (docs/API_DESIGN.md contract)."""
from __future__ import annotations

from rest_framework import serializers

from ..planner.validation import MAX_JOURNEY_OPTIONS


class EndpointSerializer(serializers.Serializer):
    """Exactly one of {location_id} or {latitude, longitude}."""

    location_id = serializers.CharField(required=False, allow_blank=False)
    latitude = serializers.FloatField(required=False)
    longitude = serializers.FloatField(required=False)

    def validate(self, attrs):
        has_id = "location_id" in attrs
        has_lat = "latitude" in attrs
        has_lon = "longitude" in attrs
        if has_id and (has_lat or has_lon):
            raise serializers.ValidationError(
                "Provide either location_id or latitude/longitude, not both."
            )
        if not has_id:
            if not (has_lat and has_lon):
                raise serializers.ValidationError(
                    "Provide location_id, or both latitude and longitude."
                )
            lat, lon = attrs["latitude"], attrs["longitude"]
            if not (-90 <= lat <= 90):
                raise serializers.ValidationError({"latitude": "Must be within [-90, 90]."})
            if not (-180 <= lon <= 180):
                raise serializers.ValidationError({"longitude": "Must be within [-180, 180]."})
        return attrs


class PlanRequestSerializer(serializers.Serializer):
    origin = EndpointSerializer()
    destination = EndpointSerializer()
    max_transfers = serializers.IntegerField(required=False, default=1, min_value=0, max_value=1)
    limit = serializers.IntegerField(
        required=False, default=5, min_value=1, max_value=MAX_JOURNEY_OPTIONS,
    )
    sort_by = serializers.ChoiceField(
        required=False, default="fewest_transfers",
        choices=["fewest_transfers", "cheapest", "fastest", "least_walking"],
    )

    def validate(self, attrs):
        # Reject unknown top-level keys explicitly.
        allowed = set(self.fields)
        extra = set(self.initial_data) - allowed
        if extra:
            raise serializers.ValidationError(
                {k: "Unknown field." for k in extra}
            )
        return attrs


class StrictSerializer(serializers.Serializer):
    """Rejects keys it does not define, at any nesting level."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            extra = set(data) - set(self.fields)
            if extra:
                raise serializers.ValidationError({key: "Unknown field." for key in sorted(extra)})
        return super().to_internal_value(data)


class RideReferenceSerializer(StrictSerializer):
    """Which ride of the trip the visitor chose. IDs only, never route facts."""

    route_pattern_id = serializers.UUIDField()
    board_occurrence_id = serializers.UUIDField()
    alight_occurrence_id = serializers.UUIDField()


class ExplainRequestSerializer(StrictSerializer):
    """The same search as /journeys/plan, plus the rides of the chosen trip.

    The server plans again and looks the trip up, so the client cannot supply
    fares, stop names or other facts for the AI to repeat.
    """

    origin = EndpointSerializer()
    destination = EndpointSerializer()
    max_transfers = serializers.IntegerField(required=False, default=1, min_value=0, max_value=1)
    sort_by = serializers.ChoiceField(
        required=False, default="fewest_transfers",
        choices=["fewest_transfers", "cheapest", "fastest", "least_walking"],
    )
    # One ride, or two when the trip has a transfer.
    rides = RideReferenceSerializer(many=True, allow_empty=False, max_length=2)
