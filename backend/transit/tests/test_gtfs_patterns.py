"""Pure grouping checks for representative trips and pattern identity."""
from __future__ import annotations

import pytest

from transit.importers.gtfs_patterns import group_patterns
from transit.importers.gtfs_types import GTFSImportError


def _trip(trip_id, *, route="R", direction="0", shape="shape"):
    return {
        "trip_id": trip_id,
        "route_id": route,
        "direction_id": direction,
        "shape_id": shape,
    }


def _stop_time(trip_id, stop_id, sequence, **overrides):
    return {
        "trip_id": trip_id,
        "stop_id": stop_id,
        "stop_sequence": str(sequence),
        "arrival_time": "08:00:00",
        "departure_time": "08:01:00",
        **overrides,
    }


def test_matching_trips_merge_after_sorting_stop_sequences():
    trips = {"first": _trip("first"), "second": _trip("second")}
    rows = [
        _stop_time("first", "B", 2),
        _stop_time("first", "A", 1),
        _stop_time("second", "A", 1, arrival_time="09:00:00"),
        _stop_time("second", "B", 2, arrival_time="09:05:00"),
    ]

    patterns = group_patterns(iter(rows), trips)

    key = ("R", "0", (("A", True, True), ("B", True, True)))
    assert list(patterns) == [key]
    assert patterns[key]["trip_count"] == 2
    assert patterns[key]["trip"] is trips["first"]
    assert [row[1] for row in patterns[key]["rows"]] == ["A", "B"]
    assert patterns[key]["rows"][0][2] == 8 * 3600


@pytest.mark.parametrize(
    "first_shape, representative",
    [("", "second"), ("first-shape", "first")],
)
def test_representative_changes_only_to_supply_a_missing_shape(first_shape, representative):
    trips = {
        "first": _trip("first", shape=first_shape),
        "second": _trip("second", shape="second-shape"),
        "third": _trip("third", shape="third-shape"),
    }
    rows = [
        _stop_time(trip_id, stop, sequence, arrival_time=arrival)
        for trip_id, arrival in [
            ("first", "08:00:00"),
            ("second", "09:00:00"),
            ("third", "10:00:00"),
        ]
        for sequence, stop in [(1, "A"), (2, "B")]
    ]

    patterns = group_patterns(iter(rows), trips)

    entry = next(iter(patterns.values()))
    assert len(patterns) == 1
    assert entry["trip_count"] == 3
    assert entry["trip"] is trips[representative]
    expected_arrival = 9 * 3600 if representative == "second" else 8 * 3600
    assert entry["rows"][0][2] == expected_arrival


@pytest.mark.parametrize(
    "difference",
    ["route", "direction", "pickup", "drop_off", "stop_order"],
)
def test_pattern_identity_preserves_route_direction_and_stop_permissions(difference):
    trips = {"first": _trip("first"), "second": _trip("second")}
    second_rows = [
        _stop_time("second", "A", 1),
        _stop_time("second", "B", 2),
    ]
    if difference == "route":
        trips["second"]["route_id"] = "OTHER"
    elif difference == "direction":
        trips["second"]["direction_id"] = "1"
    elif difference == "pickup":
        second_rows[0]["pickup_type"] = "1"
    elif difference == "drop_off":
        second_rows[1]["drop_off_type"] = "1"
    else:
        second_rows[0]["stop_id"] = "B"
        second_rows[1]["stop_id"] = "A"

    rows = [
        _stop_time("first", "A", 1),
        _stop_time("first", "B", 2),
        *second_rows,
    ]
    patterns = group_patterns(iter(rows), trips)

    assert len(patterns) == 2
    assert [entry["trip"]["trip_id"] for entry in patterns.values()] == ["first", "second"]
    assert [entry["trip_count"] for entry in patterns.values()] == [1, 1]


def test_known_trip_cannot_reappear_after_another_trip_group():
    trips = {"first": _trip("first"), "second": _trip("second")}
    rows = [
        _stop_time("first", "A", 1),
        _stop_time("second", "A", 1),
        _stop_time("first", "B", 2),
    ]

    with pytest.raises(GTFSImportError, match=r"stop_times\.txt must be grouped by trip_id\."):
        group_patterns(iter(rows), trips)


def test_approximate_times_stay_unknown_and_after_midnight_times_are_retained():
    trips = {"first": _trip("first")}
    rows = [
        _stop_time("first", "A", 1, timepoint="0"),
        _stop_time(
            "first", "B", 2,
            arrival_time="25:10:00", departure_time="25:11:00",
        ),
    ]

    patterns = group_patterns(iter(rows), trips)
    grouped_rows = next(iter(patterns.values()))["rows"]

    assert grouped_rows[0][2:4] == (None, None)
    assert grouped_rows[1][2:4] == (90600, 90660)


def test_invalid_sequences_are_skipped_without_losing_the_final_trip():
    trips = {"first": _trip("first")}
    rows = [
        _stop_time("first", "ignored", "invalid"),
        _stop_time("first", "A", 1),
        _stop_time("first", "B", 2),
    ]

    patterns = group_patterns(iter(rows), trips)
    entry = next(iter(patterns.values()))

    assert len(patterns) == 1
    assert entry["trip_count"] == 1
    assert [row[1] for row in entry["rows"]] == ["A", "B"]