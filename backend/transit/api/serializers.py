"""DRF serializers for request validation (docs/API_DESIGN.md contract)."""
from __future__ import annotations

from rest_framework import serializers


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
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=5)
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
