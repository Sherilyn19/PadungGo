"""
Spatial-field compatibility layer.

In PostGIS mode we use real GeoDjango geometry fields (Point / LineString) with
GiST indexes. In lite mode (no GDAL/GEOS) we fall back to plain float columns
for coordinates and a text column for serialized geometry, so the schema and the
pure-Python planner remain exercisable without spatial system libraries.

Canonical convention everywhere: WGS84 / SRID 4326, (latitude, longitude).
GeoJSON output uses [longitude, latitude]; API objects name lat/lon explicitly.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models

GIS_ENABLED: bool = getattr(settings, "GIS_ENABLED", False)

if GIS_ENABLED:  # pragma: no cover - requires GDAL/GEOS at import time
    from django.contrib.gis.db import models as gis_models

    # Geometry is optional: lat/lon float columns are the canonical coordinates;
    # the spatial column is populated when available (e.g. by importers).
    def point_field(**kwargs):
        kwargs.setdefault("srid", 4326)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        return gis_models.PointField(**kwargs)

    def linestring_field(**kwargs):
        kwargs.setdefault("srid", 4326)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        return gis_models.LineStringField(**kwargs)

    SPATIAL_INDEX_SUPPORTED = True
else:
    # Lite mode: coordinates stored as a JSON dict {"lat":..., "lon":...};
    # geometry stored as GeoJSON text. Keeps migrations and the planner usable.
    def point_field(**kwargs):
        kwargs.pop("srid", None)
        kwargs.pop("geography", None)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        return models.JSONField(**kwargs)

    def linestring_field(**kwargs):
        kwargs.pop("srid", None)
        kwargs.setdefault("null", True)
        kwargs.setdefault("blank", True)
        return models.JSONField(**kwargs)

    SPATIAL_INDEX_SUPPORTED = False


def make_point(lat: float, lon: float):
    """Value for a point_field() column in the active mode."""
    if GIS_ENABLED:  # pragma: no cover - requires GDAL/GEOS
        from django.contrib.gis.geos import Point

        return Point(lon, lat, srid=4326)
    return {"lat": lat, "lon": lon}


def make_linestring(latlons):
    """Value for a linestring_field() column. latlons: [(lat, lon), ...]."""
    pts = [(lon, lat) for lat, lon in latlons]
    if len(pts) < 2:
        return None
    if GIS_ENABLED:  # pragma: no cover - requires GDAL/GEOS
        from django.contrib.gis.geos import LineString

        return LineString(pts, srid=4326)
    return {"type": "LineString", "coordinates": [list(p) for p in pts]}


def linestring_coords(value):
    """GeoJSON-order [[lon, lat], ...] from a stored linestring, or None."""
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get("coordinates")
    return [list(c) for c in value.coords]  # GEOS LineString
