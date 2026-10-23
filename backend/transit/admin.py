"""Django Admin for development, review and demonstration data management."""
from __future__ import annotations

import csv
import zipfile
from dataclasses import dataclass

from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.validators import FileExtensionValidator
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path

from .planner.loader import invalidate_network_cache
from .importers.osm_route import (
    OSMRouteError,
    apply_extensions,
    download_command,
    parse_osm_route,
    plan_extension,
)
from .importers.gtfs import GTFSImportError, ImportOptions, import_gtfs
from .places.osm_import import (
    CITY_NAMES,
    OSMImportError,
    import_osm_file,
    import_osm_places,
    powershell_download_command,
)
from .models.enums import VehicleClass

from .models import (
    Area,
    DataSource,
    FareRule,
    Location,
    PatternStop,
    ProviderUsage,
    RecordEvidence,
    Route,
    RouteEvidence,
    RoutePattern,
    RouteSegment,
    Stop,
    TransferConnection,
)


class GTFSImportForm(forms.Form):
    feed = forms.FileField(
        help_text="GTFS .zip file (max 50 MB).",
        validators=[FileExtensionValidator(allowed_extensions=["zip"])],
    )

    def clean_feed(self):
        feed = self.cleaned_data["feed"]
        limit = settings.GTFS_UPLOAD_MAX_BYTES
        if feed.size > limit:
            raise forms.ValidationError(f"File is larger than {limit // (1024 * 1024)} MB.")
        # The extension can be renamed, so also check the file's contents
        # really are a zip archive before handing it to the importer.
        if not zipfile.is_zipfile(feed):
            raise forms.ValidationError("The file is not a valid zip archive.")
        feed.seek(0)
        return feed

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
            d = form.cleaned_data
            try:
                report = import_gtfs(d["feed"], ImportOptions(
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


def _osm_report_text(result) -> str:
    cities = ", ".join(f"{city}: {count}" for city, count in sorted(result.by_city.items()))
    timing = f"Saved in {result.save_seconds:.1f}s"
    if result.download_seconds is not None:
        timing = f"Downloaded in {result.download_seconds:.0f}s. {timing}"
    return (f"Done. {result.created} added, {result.updated} updated, "
            f"{result.unchanged} unchanged ({cities}). {timing}.")


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "aliases", "kind", "area", "status", "latitude", "longitude")
    list_filter = ("kind", "status")
    search_fields = ("name", "aliases")
    change_list_template = "admin/transit/location_changelist.html"

    def get_urls(self):
        extra = [path("import-osm/", self.admin_site.admin_view(self.import_osm_view),
                      name="transit_import_osm_places")]
        return extra + super().get_urls()

    def import_osm_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        report = error = None
        chosen_city = request.POST.get("city") if request.POST.get("city") in CITY_NAMES else CITY_NAMES[0]
        if request.method == "POST":
            try:
                if "file" in request.FILES:
                    result = import_osm_file(request.FILES["file"].read())
                else:
                    result = import_osm_places(chosen_city)
                report = _osm_report_text(result)
            except OSMImportError as exc:
                error = str(exc)
        context = {**self.admin_site.each_context(request), "report": report, "error": error,
                   "cities": CITY_NAMES, "chosen_city": chosen_city,
                   "download_commands": [(name, powershell_download_command(name)) for name in CITY_NAMES],
                   "title": "Import places from OpenStreetMap"}
        return TemplateResponse(request, "admin/transit/osm_places_import.html", context)


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "status", "can_board", "can_alight", "latitude", "longitude")
    list_filter = ("status", "can_board", "can_alight")
    search_fields = ("name",)


# Pattern stops and segments are shown read-only. Editable inlines rendered a
# dropdown of every Stop per stop row and, per segment row, two dropdowns of
# every PatternStop in the database, each option label running extra queries.
# On the full GTFS import that grows with (rows x all pattern stops) and the
# page cannot finish. Ordered stops are corrected through previewed data
# changes instead, so distances, segments and transfers stay consistent.
class PatternStopInline(admin.TabularInline):
    model = PatternStop
    extra = 0
    can_delete = False
    ordering = ("sequence",)
    fields = ("sequence", "stop_name", "stop_coordinates", "distance_along_m",
              "can_board", "can_alight")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("stop", "pattern__route")

    @admin.display(description="Stop")
    def stop_name(self, obj):
        return obj.stop.name

    @admin.display(description="Latitude, longitude")
    def stop_coordinates(self, obj):
        return f"{obj.stop.latitude:.6f}, {obj.stop.longitude:.6f}"


class RouteSegmentInline(admin.TabularInline):
    model = RouteSegment
    extra = 0
    can_delete = False
    fields = ("from_sequence", "to_sequence", "distance_m", "riding_seconds",
              "estimate_basis", "source")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "pattern__route", "from_occurrence", "to_occurrence", "source")

    @admin.display(description="From stop #")
    def from_sequence(self, obj):
        return obj.from_occurrence.sequence

    @admin.display(description="To stop #")
    def to_sequence(self, obj):
        return obj.to_occurrence.sequence


class StopStretchForm(forms.Form):
    keep_stop = forms.CharField(
        label="Last stop to keep", max_length=200,
        initial="Kamagong Street / J. Solon Drive",
        help_text="Exact stop name. The first time the route reaches it counts.",
    )
    last_stop = forms.CharField(
        label="Last stop to switch off", max_length=200,
        initial="M. J. Cuenco Avenue & Osmena Boulevard",
        help_text="Exact stop name, found after the kept stop. Every stop in between is included.",
    )
    mode = forms.ChoiceField(
        label="What to do",
        choices=[("off", "Switch off boarding and getting off"), ("on", "Switch them back on")],
        initial="off", widget=forms.RadioSelect,
    )


@dataclass
class StretchPlan:
    pattern: RoutePattern
    stops: list
    problem: str = ""


def plan_stretch(pattern: RoutePattern, keep_stop: str, last_stop: str) -> StretchPlan:
    """The stops after `keep_stop` up to and including `last_stop` (first matches only)."""
    stops = list(pattern.pattern_stops.select_related("stop").order_by("sequence"))
    names = [occurrence.stop.name.casefold() for occurrence in stops]
    keep, last = keep_stop.strip().casefold(), last_stop.strip().casefold()
    if keep not in names:
        return StretchPlan(pattern, [], f"No stop named \u201c{keep_stop.strip()}\u201d on this route.")
    keep_at = names.index(keep)
    if last not in names[keep_at + 1:]:
        return StretchPlan(pattern, [], f"\u201c{last_stop.strip()}\u201d does not come after the kept stop.")
    last_at = names.index(last, keep_at + 1)
    return StretchPlan(pattern, stops[keep_at + 1:last_at + 1])


def apply_stretch(plans: list, switch_on: bool) -> int:
    """Flip only the boarding/getting-off switches. Distances, segments and transfers stay as they are."""
    ids = [occurrence.pk for plan in plans for occurrence in plan.stops]
    with transaction.atomic():
        PatternStop.objects.filter(pk__in=ids).update(can_board=switch_on, can_alight=switch_on)
        invalidate_network_cache()  # QuerySet.update() sends no signals
    return len(ids)


@admin.action(description="Switch stops off or on along a stretch (preview first)", permissions=["change"])
def adjust_stop_stretch(modeladmin, request, queryset):
    if not request.user.is_superuser:
        raise PermissionDenied
    step = request.POST.get("step", "")
    form = StopStretchForm(request.POST if step else None)
    patterns = list(queryset.select_related("route").order_by("route__code", "variant_key"))
    plans = None
    if step in ("preview", "apply") and form.is_valid():
        data = form.cleaned_data
        plans = [plan_stretch(p, data["keep_stop"], data["last_stop"]) for p in patterns]
        if step == "apply" and not any(plan.problem for plan in plans):
            count = apply_stretch(plans, data["mode"] == "on")
            state = "on" if data["mode"] == "on" else "off"
            modeladmin.message_user(request, f"Done. Boarding and getting off switched {state} for {count} stops "
                                             f"on {len(plans)} routes.")
            return None
    context = {
        **modeladmin.admin_site.each_context(request), "title": "Switch stops off or on",
        "form": form, "plans": plans, "can_apply": bool(plans) and not any(p.problem for p in plans),
        "selected": [str(p.pk) for p in patterns], "action_name": "adjust_stop_stretch",
        "patterns": patterns, "opts": modeladmin.model._meta,
    }
    return TemplateResponse(request, "admin/transit/stop_stretch.html", context)


@admin.action(description="Add stops at the start from an OpenStreetMap route (preview first)", permissions=["change"])
def extend_start_from_osm(modeladmin, request, queryset):
    if not request.user.is_superuser:
        raise PermissionDenied
    step = request.POST.get("step", "")
    join_stop = (request.POST.get("join_stop") or "Ginebra San Miguel").strip()
    patterns = list(queryset.select_related("route").order_by("route__code", "variant_key"))
    plans = route = None
    payload = error = ""
    try:
        if step == "preview":
            upload = request.FILES.get("route_file")
            if upload is None:
                raise OSMRouteError("Choose the downloaded file first.")
            raw = upload.read(MAX_UPLOAD_BYTES + 1)
            route = parse_osm_route(raw)
            payload = raw.decode("utf-8")
        elif step == "apply":
            payload = request.POST.get("payload", "")
            route = parse_osm_route(payload.encode("utf-8"))
        if route is not None:
            plans = [plan_extension(p, route, join_stop) for p in patterns]
            if step == "apply" and not any(plan.problem for plan in plans):
                added = apply_extensions(plans, route)
                modeladmin.message_user(request, f"Done. Added {added // max(len(plans), 1)} stops at the start of "
                                                 f"{len(plans)} routes.")
                return None
    except (OSMRouteError, UnicodeDecodeError) as exc:
        error = str(exc) if isinstance(exc, OSMRouteError) else "That file is not readable text."
        plans = None
    context = {
        **modeladmin.admin_site.each_context(request), "title": "Add stops at the start of a route",
        "plans": plans, "can_apply": bool(plans) and not any(p.problem for p in plans),
        "route": route, "payload": payload, "error": error, "join_stop": join_stop,
        "selected": [str(p.pk) for p in patterns], "patterns": patterns,
        "action_name": "extend_start_from_osm", "download_command": download_command(),
        "opts": modeladmin.model._meta,
    }
    return TemplateResponse(request, "admin/transit/extend_from_osm.html", context)


MAX_UPLOAD_BYTES = 5 * 1024 * 1024


# Spreadsheet apps run cells starting with these characters as formulas.
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _safe_cell(value):
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


ORDERED_STOP_COLUMNS = (
    "route_id", "route_code", "route_name", "route_active", "service_availability",
    "pattern_id", "variant_key", "direction", "signboard", "pattern_status",
    "sequence", "stop_id", "stop_name", "latitude", "longitude",
    "distance_along_m", "can_board", "can_alight", "segment_to_next_m",
)


def ordered_stop_rows(patterns):
    """Yield one export row per stop occurrence, in pattern order."""
    for pattern in patterns:
        route = pattern.route
        next_distance = {seg.from_occurrence_id: seg.distance_m for seg in pattern.segments.all()}
        for occ in pattern.pattern_stops.all():
            yield (
                route.id, route.code, _safe_cell(route.name), route.active,
                route.service_availability, pattern.id, _safe_cell(pattern.variant_key),
                pattern.direction, _safe_cell(pattern.signboard), pattern.status,
                occ.sequence, occ.stop_id, _safe_cell(occ.stop.name),
                occ.stop.latitude, occ.stop.longitude, occ.distance_along_m,
                occ.can_board, occ.can_alight, next_distance.get(occ.id, ""),
            )


@admin.action(description="Export ordered stops as CSV (read-only)", permissions=["view"])
def export_ordered_stops(modeladmin, request, queryset):
    """Download stored stops for the selected patterns, including unverified ones.

    Staff-only through Django Admin; it publishes nothing on the public API.
    """
    patterns = (
        queryset.select_related("route")
        .prefetch_related(
            Prefetch("pattern_stops",
                     queryset=PatternStop.objects.select_related("stop").order_by("sequence")),
            "segments",
        )
        .order_by("route__code", "route_id", "direction", "variant_key")
    )
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="pattern_ordered_stops.csv"'
    # The byte-order mark lets Excel read accented names such as Osmeña correctly.
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(ORDERED_STOP_COLUMNS)
    writer.writerows(ordered_stop_rows(patterns))
    return response


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "vehicle_class", "operator",
        "active", "service_availability",
    )
    list_filter = ("vehicle_class", "active", "service_availability")
    search_fields = ("code", "name", "operator")


@admin.register(RoutePattern)
class RoutePatternAdmin(admin.ModelAdmin):
    list_display = ("route", "direction", "variant_key", "signboard", "status", "verified_at")
    list_filter = ("direction", "status", "route__vehicle_class")
    search_fields = ("route__code", "signboard", "variant_key")
    list_select_related = ("route",)
    actions = [export_ordered_stops, adjust_stop_stretch, extend_start_from_osm]
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


@admin.register(ProviderUsage)
class ProviderUsageAdmin(admin.ModelAdmin):
    """Daily Geoapify request counts, for checking the free-plan quota."""

    list_display = ("day", "provider", "requests")
    list_filter = ("provider",)
    ordering = ("-day",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
