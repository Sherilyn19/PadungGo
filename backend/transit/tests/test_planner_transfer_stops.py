"""Transfer-stop eligibility using synthetic data only; no database."""
from dataclasses import replace
from datetime import date

import pytest

from transit.planner import plan_journeys
from transit.planner.journey_types import Endpoint, PlanRequest
from transit.tests.planner_fixtures import base_network


def _req():
    return PlanRequest(
        origin=Endpoint(10.300, 123.900),
        destination=Endpoint(10.3005, 123.936),
        query_date=date(2026, 6, 1),
        max_transfers=1,
    )


def _plan(network, historical=False):
    return plan_journeys(
        network,
        _req(),
        config={
            "ALLOW_DOCUMENTED": historical,
            "STOP_SEARCH_RADIUS_M": 500,
        },
    )


def _assert_no_journey(result):
    assert result.journey_options == []
    assert result.reason == "no_journey_within_mvp_limits"


def _assert_transfer(result, from_stop, to_stop):
    assert result.reason is None
    assert len(result.journey_options) == 1
    option = result.journey_options[0]
    assert option["transfers"] == 1
    transfers = [
        segment for segment in option["segments"]
        if segment["mode"] == "transfer_walk"
    ]
    assert len(transfers) == 1
    assert transfers[0]["from_stop_id"] == from_stop
    assert transfers[0]["to_stop_id"] == to_stop
    return transfers[0]


def _replace_occurrence(network, occurrence_id, **changes):
    for index, pattern in enumerate(network.patterns):
        if any(stop.id == occurrence_id for stop in pattern.stops):
            network.patterns[index] = replace(
                pattern,
                stops=tuple(
                    replace(stop, **changes) if stop.id == occurrence_id else stop
                    for stop in pattern.stops
                ),
            )
            return
    raise AssertionError(f"Missing test occurrence: {occurrence_id}")


def _same_stop_network():
    network = base_network()
    _replace_occurrence(network, "B-o1", stop_id="S3")
    network.transfers = [
        replace(
            network.transfers[0],
            from_stop_id="S3",
            to_stop_id="S3",
            distance_m=0,
            duration_seconds=0,
        )
    ]
    return network


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize("stop_id", ["S3", "S5"])
@pytest.mark.parametrize(
    "status", ["candidate", "documented", "needs_review", "retired"]
)
def test_transfer_stop_status_respects_mode(historical, stop_id, status):
    network = base_network()
    network.stops[stop_id] = replace(network.stops[stop_id], status=status)

    result = _plan(network, historical)

    if historical and status == "documented":
        _assert_transfer(result, "S3", "S5")
    else:
        _assert_no_journey(result)


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize(
    "stop_id,permission",
    [("S3", "can_alight"), ("S5", "can_board")],
)
def test_transfer_requires_stop_permission(historical, stop_id, permission):
    network = base_network()
    network.stops[stop_id] = replace(
        network.stops[stop_id], **{permission: False}
    )

    _assert_no_journey(_plan(network, historical))


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
def test_transfer_ignores_permissions_for_unused_actions(historical):
    network = base_network()
    network.stops["S3"] = replace(network.stops["S3"], can_board=False)
    network.stops["S5"] = replace(network.stops["S5"], can_alight=False)

    _assert_transfer(_plan(network, historical), "S3", "S5")


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize(
    "occurrence_id,permission",
    [("A-o3", "can_alight"), ("B-o1", "can_board")],
)
def test_transfer_preserves_occurrence_permissions(
    historical, occurrence_id, permission
):
    network = base_network()
    _replace_occurrence(network, occurrence_id, **{permission: False})

    _assert_no_journey(_plan(network, historical))


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize(
    "status", ["documented", "candidate", "needs_review"]
)
def test_transfer_preserves_connection_status(historical, status):
    network = base_network()
    network.transfers = [
        replace(network.transfers[0], status=status)
    ]

    result = _plan(network, historical)

    if historical and status == "documented":
        _assert_transfer(result, "S3", "S5")
    else:
        _assert_no_journey(result)


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize("stop_id", ["S3", "S5"])
def test_missing_transfer_stop_is_skipped(historical, stop_id):
    network = base_network()
    del network.stops[stop_id]

    _assert_no_journey(_plan(network, historical))


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
def test_valid_same_stop_transfer_is_preserved(historical):
    network = _same_stop_network()

    transfer = _assert_transfer(_plan(network, historical), "S3", "S3")

    assert transfer["distance_m"] == 0


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize("permission", ["can_alight", "can_board"])
def test_same_stop_transfer_requires_both_permissions(historical, permission):
    network = _same_stop_network()
    network.stops["S3"] = replace(
        network.stops["S3"], **{permission: False}
    )

    _assert_no_journey(_plan(network, historical))


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
def test_same_stop_transfer_respects_documented_status(historical):
    network = _same_stop_network()
    network.stops["S3"] = replace(network.stops["S3"], status="documented")

    result = _plan(network, historical)

    if historical:
        _assert_transfer(result, "S3", "S3")
    else:
        _assert_no_journey(result)


@pytest.mark.parametrize("historical", [False, True], ids=["strict", "historical"])
@pytest.mark.parametrize("blocked_stop", ["S3", "S5"])
def test_blocked_transfer_does_not_hide_valid_alternative(
    historical, blocked_stop
):
    network = base_network()
    network.transfers.append(
        replace(
            network.transfers[0],
            id="T-2",
            from_stop_id="S4",
            to_stop_id="S6",
        )
    )
    network.stops[blocked_stop] = replace(
        network.stops[blocked_stop], status="needs_review"
    )

    _assert_transfer(_plan(network, historical), "S4", "S6")
