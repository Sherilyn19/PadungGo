"""Django Admin for development, review and demonstration data management."""
from __future__ import annotations

from django.contrib import admin

from .models import (
    Area,
    DataSource,
    FareRule,
    Location,
    PatternStop,
    RecordEvidence,
    Route,
    RouteEvidence,
    RoutePattern,
    RouteSegment,
    Stop,
    TransferConnection,
)


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("title", "publisher", "published_at", "collected_at", "license")
    search_fields = ("title", "publisher", "reference")


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "parent")
    list_filter = ("kind",)
    search_fields = ("name",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "area", "status", "latitude", "longitude")
    list_filter = ("kind", "status")
    search_fields = ("name",)


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "status", "can_board", "can_alight", "latitude", "longitude")
    list_filter = ("status", "can_board", "can_alight")
    search_fields = ("name",)


class PatternStopInline(admin.TabularInline):
    model = PatternStop
    extra = 0
    ordering = ("sequence",)


class RouteSegmentInline(admin.TabularInline):
    model = RouteSegment
    extra = 0


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "vehicle_class", "operator", "active")
    list_filter = ("vehicle_class", "active")
    search_fields = ("code", "name", "operator")


@admin.register(RoutePattern)
class RoutePatternAdmin(admin.ModelAdmin):
    list_display = ("route", "direction", "variant_key", "signboard", "status", "verified_at")
    list_filter = ("direction", "status", "route__vehicle_class")
    search_fields = ("route__code", "signboard", "variant_key")
    inlines = [PatternStopInline, RouteSegmentInline]


@admin.register(TransferConnection)
class TransferConnectionAdmin(admin.ModelAdmin):
    list_display = ("from_stop", "to_stop", "distance_m", "duration_seconds", "status")
    list_filter = ("status",)


@admin.register(FareRule)
class FareRuleAdmin(admin.ModelAdmin):
    list_display = ("vehicle_class", "passenger_category", "kind", "route", "pattern",
                    "valid_from", "valid_until", "status")
    list_filter = ("vehicle_class", "passenger_category", "kind", "status")


@admin.register(RouteEvidence)
class RouteEvidenceAdmin(admin.ModelAdmin):
    list_display = ("pattern", "status", "source", "reviewed_at", "reviewer")
    list_filter = ("status",)
    # Evidence is append-only; discourage edits/deletes from admin.
    def has_change_permission(self, request, obj=None):
        return obj is None


@admin.register(RecordEvidence)
class RecordEvidenceAdmin(admin.ModelAdmin):
    list_display = ("status", "source", "reviewed_at", "reviewer")
    list_filter = ("status",)
