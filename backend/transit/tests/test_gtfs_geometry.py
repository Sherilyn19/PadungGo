"""Numeric checks for shared distance calculations and GTFS projections."""
from __future__ import annotations

import pytest

from transit.importers.gtfs import ImportOptions, import_gtfs
from transit.importers.gtfs_geometry import project_stops
from transit.models import PatternStop
from transit.planner.geo import haversine_m
from transit.tests.test_gtfs_import import _feed


def test_haversine_known_equatorial_distance():
    distance = haversine_m(0.0, 0.0, 0.0, 1.0)
    assert distance == pytest.approx(111194.92664455874, rel=0, abs=1e-6)


def test_zero_length_shape_segment():
    point = (10.3, 123.9)
    assert haversine_m(*point, *point) == 0.0
    projections = project_stops([point, point], [point, point])
    assert projections is not None
    assert [projection.along_m for projection in projections] == [0.0, 0.0]
    assert [projection.offset_m for projection in projections] == [0.0, 0.0]


def test_cumulative_shape_distance():
    shape = [(0.0, 0.0), (0.0, 0.01), (0.0, 0.02)]
    projections = project_stops(shape, shape)
    assert projections is not None
    assert [projection.along_m for projection in projections] == pytest.approx(
        [0.0, 1111.9492664455875, 2223.898532891175],
        rel=0,
        abs=1e-6,
    )
    assert [int(round(projection.along_m)) for projection in projections] == [0, 1112, 2224]


@pytest.mark.django_db
def test_imported_fixture_distances_keep_exact_metre_rounding():
    import_gtfs(_feed(), ImportOptions(source_title="Geometry regression feed"))
    route_x = list(
        PatternStop.objects.filter(pattern__route__code="TX")
        .order_by("sequence")
        .values_list("stop__name", "distance_along_m")
    )
    route_y = list(
        PatternStop.objects.filter(pattern__route__code="TY")
        .order_by("sequence")
        .values_list("stop__name", "distance_along_m")
    )
    assert route_x == [("West", 0), ("Middle", 985), ("East Hub", 1969)]
    assert route_y == [("East Hub", 0), ("North", 1001)]
