"""Focused checks for journey identity, ordering, and returned labels."""
from __future__ import annotations

from copy import deepcopy

import pytest

from transit.planner.journey_types import Endpoint, PlanRequest
from transit.planner.ranking import (
    apply_labels,
    deduplicate_options,
    journey_key,
    rank_options,
)
from transit.planner.responses import journey_result


def _option(
    name, *, transfers=0, ride_m=1000, walk_m=100, fare=1000, seconds=300,
    fare_status="exact",
):
    return {
        "marker": name,
        "transfers": transfers,
        "labels": [],
        "segments": [],
        "fare": {
            "total_centavos": fare,
            "total_is_complete": fare is not None,
            "status": fare_status if fare is not None else "unavailable",
        },
        "time": {
            "total_seconds": seconds,
            "total_is_complete": seconds is not None,
        },
        "_dedup_key": (("ride", name, "board", "alight"),),
        "_walk_known_m": walk_m,
        "_ride_m": ride_m,
    }


def test_journey_identity_uses_occurrences_and_directed_transfers():
    segments = [
        {"mode": "walk", "straight_line_m": 10},
        {
            "mode": "ride",
            "route_pattern_id": "P1",
            "board_occurrence_id": "A",
            "alight_occurrence_id": "B",
        },
        {"mode": "transfer_walk", "from_stop_id": "S1", "to_stop_id": "S2"},
        {
            "mode": "ride",
            "route_pattern_id": "P2",
            "board_occurrence_id": "C",
            "alight_occurrence_id": "D",
        },
    ]
    expected = (
        ("ride", "P1", "A", "B"),
        ("transfer", "S1", "S2"),
        ("ride", "P2", "C", "D"),
    )
    assert journey_key(segments) == expected

    changed = deepcopy(segments)
    changed[0]["straight_line_m"] = 200
    assert journey_key(changed) == expected

    changed[1]["board_occurrence_id"] = "A-repeat"
    assert journey_key(changed) != expected

    changed = deepcopy(segments)
    changed[2].update(from_stop_id="S2", to_stop_id="S1")
    assert journey_key(changed) != expected


def test_deduplication_keeps_first_option_and_input_order():
    first = _option("A", fare=None)
    duplicate = _option("A", fare=100)
    second = _option("B")
    options = [first, second, duplicate]

    result = deduplicate_options(options)

    assert len(result) == 2
    assert result[0] is first
    assert result[1] is second
    assert len(options) == 3


def test_fewest_transfers_uses_ride_then_walk_then_identity():
    options = [
        _option("transfer", transfers=1, ride_m=1, walk_m=0),
        _option("long", ride_m=1000, walk_m=0),
        _option("more-walking", ride_m=900, walk_m=300),
        _option("Z", ride_m=900, walk_m=200),
        _option("A", ride_m=900, walk_m=200),
    ]

    ranked, ranking = rank_options(options, "fewest_transfers")

    assert [option["marker"] for option in ranked] == [
        "A", "Z", "more-walking", "long", "transfer",
    ]
    assert ranking == {
        "requested": "fewest_transfers",
        "applied": "fewest_transfers",
        "warning": None,
    }


def test_cheapest_uses_complete_fares_then_transfers_then_identity():
    options = [
        _option("expensive", fare=2000),
        _option("transfer", transfers=1, fare=1000),
        _option("Z", fare=1000),
        _option("A", fare=1000),
        _option("free", transfers=1, fare=0),
    ]

    ranked, ranking = rank_options(options, "cheapest")

    assert [option["marker"] for option in ranked] == [
        "free", "A", "Z", "transfer", "expensive",
    ]
    assert ranking == {"requested": "cheapest", "applied": "cheapest", "warning": None}


def test_fastest_uses_complete_times_then_transfers_then_identity():
    options = [
        _option("slow", seconds=600),
        _option("transfer", transfers=1, seconds=300),
        _option("Z", seconds=300),
        _option("A", seconds=300),
        _option("zero", transfers=1, seconds=0),
    ]

    ranked, ranking = rank_options(options, "fastest")

    assert [option["marker"] for option in ranked] == [
        "zero", "A", "Z", "transfer", "slow",
    ]
    assert ranking == {"requested": "fastest", "applied": "fastest", "warning": None}


@pytest.mark.parametrize(
    "sort_by, warning",
    [
        (
            "cheapest",
            "Cannot fairly rank by cheapest: some fares are approximate or unavailable. Fell back to fewest_transfers.",
        ),
        (
            "fastest",
            "Cannot fairly rank by fastest: some durations are unknown. Fell back to fewest_transfers.",
        ),
        (
            "least_walking",
            "Cannot fairly rank by least_walking: walking distances are approximate. Fell back to fewest_transfers.",
        ),
    ],
)
def test_incomparable_options_fall_back_with_exact_warning(sort_by, warning):
    options = [
        _option("known", transfers=1, fare=0, seconds=0, walk_m=0),
        _option("unknown", fare=None, seconds=None, walk_m=500),
    ]

    ranked, ranking = rank_options(options, sort_by)

    assert [option["marker"] for option in ranked] == ["unknown", "known"]
    assert ranking == {
        "requested": sort_by,
        "applied": "fewest_transfers",
        "warning": warning,
    }


def test_labels_include_complete_zero_totals_and_all_ties():
    unknown = _option("unknown", fare=None, seconds=None)
    first = _option("A", fare=0, seconds=0)
    second = _option("B", fare=0, seconds=0)

    apply_labels([unknown, first, second])

    assert unknown["labels"] == ["fewest_transfers"]
    # An unpriced alternative prevents a fair cheapest comparison.
    assert first["labels"] == ["fewest_transfers", "fastest"]
    assert second["labels"] == ["fewest_transfers", "fastest"]


def test_response_limits_before_labels_and_removes_internal_fields():
    retained = _option("retained", fare=2000, seconds=None)
    excluded = _option("excluded", transfers=1, fare=1000, seconds=None)
    request = PlanRequest(
        origin=Endpoint(10.3, 123.9),
        destination=Endpoint(10.31, 123.91),
        limit=1,
    )

    result = journey_result(
        [excluded, retained], request,
        allow_documented=False, response_prefix="journey",
    )

    assert len(result.journey_options) == 1
    option = result.journey_options[0]
    assert option["marker"] == "retained"
    assert option["id"] == "journey-1"
    assert option["labels"] == ["fewest_transfers", "cheapest"]
    assert excluded["labels"] == []
    assert not {"_dedup_key", "_walk_known_m", "_ride_m"} & option.keys()
    assert "_dedup_key" in retained



@pytest.mark.parametrize("fare_status", ["approximate", "unavailable", None])
def test_non_exact_amounts_cannot_control_cheapest_ranking(fare_status):
    uncertain = _option(
        "uncertain", fare=100, fare_status=fare_status, ride_m=9000,
    )
    exact = _option("exact", fare=2000, ride_m=1000)

    ranked, ranking = rank_options([uncertain, exact], "cheapest")
    apply_labels(ranked)

    assert [option["marker"] for option in ranked] == ["exact", "uncertain"]
    assert ranking["applied"] == "fewest_transfers"
    assert "approximate or unavailable" in ranking["warning"]
    assert all("cheapest" not in option["labels"] for option in ranked)


def test_exact_zero_fares_receive_cheapest_labels_for_all_ties():
    first = _option("A", fare=0, seconds=None)
    second = _option("B", fare=0, seconds=None)

    apply_labels([first, second])

    assert first["labels"] == ["fewest_transfers", "cheapest"]
    assert second["labels"] == ["fewest_transfers", "cheapest"]
