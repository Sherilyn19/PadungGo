"""Django Admin for development, review and demonstration data management."""
from __future__ import annotations

from django import forms
from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.urls import path

from .importers.gtfs import GTFSImportError, ImportOptions, import_gtfs
from .models.enums import VehicleClass

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


class GTFSImportForm(forms.Form):
    feed = forms.FileField(help_text="GTFS .zip file (max 50 MB).")
    title = forms.CharField(max_length=300, initial="Cebu DOTC GTFS (Transitland archive)")
    reference = forms.CharField(max_length=1000, required=False,
                                initial="https://www.transit.land/feeds/f-wcb4-cebu~dotc")
    publisher = forms.CharField(max_length=300, required=False,
                                initial="Department of Transportation, Cebu (DOTC) via Transitland")
    license = forms.CharField(max_length=300, required=False,
                              help_text="Record the reuse terms you confirmed for this feed.")
    published_at = forms.DateField(required=False, help_text="YYYY-MM-DD, if known.")
    limitations = forms.CharField(widget=forms.Textarea, required=False, initial=(
        "Historic GTFS archive; service dates 2014-02-01 to 2017-02-01. Current operation, "
        "stops and directions are NOT field-verified."))
    vehicle_class = forms.ChoiceField(choices=VehicleClass.choices, initial=VehicleClass.JEEPNEY,
                                      help_text="Used when the feed does not say.")
    same_stop_transfers = forms.BooleanField(required=False, initial=True,
                                             help_text="Allow reboarding at a stop shared by routes.")


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("title", "publisher", "published_at", "collected_at", "license")
    search_fields = ("title", "publisher", "reference")
    change_list_template = "admin/transit/datasource_changelist.html"

    def get_urls(self):
        extra = [path("import-gtfs/", self.admin_site.admin_view(self.import_gtfs_view),
                      name="transit_import_gtfs")]
        return extra + super().get_urls()

    def import_gtfs_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        report = error = None
        form = GTFSImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            feed = form.cleaned_data["feed"]
            if feed.size > 50 * 1024 * 1024:
                error = "File is larger than 50 MB."
            else:
                d = form.cleaned_data
                try:
                    report = import_gtfs(feed, ImportOptions(
                        source_title=d["title"], source_reference=d["reference"],
                        source_publisher=d["publisher"], source_license=d["license"],
                        source_published_at=d["published_at"], source_limitations=d["limitations"],
                        default_vehicle_class=d["vehicle_class"],
                        same_stop_transfers=d["same_stop_transfers"],
                    )).summary()
                except GTFSImportError as exc:
                    error = str(exc)
        context = {**self.admin_site.each_context(request), "form": form,
                   "report": report, "error": error, "title": "Import GTFS feed"}
        return TemplateResponse(request, "admin/transit/gtfs_import.html", context)


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
