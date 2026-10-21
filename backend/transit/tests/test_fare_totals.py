"""Fare aggregation tests, not evidence for production route prices."""
from transit.planner.fare_totals import summarise_fares


def _ride(pattern_id, amount, status="exact", reason=None):
    return {
        "route_pattern_id": pattern_id,
        "fare": {
            "amount_centavos": amount,
            "rule_id": f"test-rule-{pattern_id}",
            "passenger_category": "regular",
            "source_ids": ["test-source"],
            "effective_date": "2026-09-28",
            "assumptions": None,
            "status": status,
            "reason": reason,
        },
    }


def test_exact_fares_produce_exact_complete_total():
    result = summarise_fares([
        _ride("P-A", 1400),
        _ride("P-B", 1600),
    ])

    assert result["total_centavos"] == 3000
    assert result["known_subtotal_centavos"] == 3000
    assert result["total_is_complete"] is True
    assert result["status"] == "exact"
    assert result["reason"] is None
    assert result["per_leg"][0]["source_ids"] == ["test-source"]
    assert result["per_leg"][0]["effective_date"] == "2026-09-28"


def test_one_approximate_leg_makes_the_total_approximate():
    reason = "Based on an estimated ride distance."
    result = summarise_fares([
        _ride("P-A", 1400),
        _ride("P-B", 1950, "approximate", reason),
    ])

    assert result["total_centavos"] == 3350
    assert result["known_subtotal_centavos"] == 3350
    assert result["total_is_complete"] is True
    assert result["status"] == "approximate"
    assert result["per_leg"][1]["reason"] == reason


def test_unavailable_leg_prevents_complete_total():
    reason = "Fare depends on the vehicle you board."
    result = summarise_fares([
        _ride("P-A", 1400, "approximate", "Recorded distance is approximate."),
        _ride("P-B", None, "unavailable", reason),
    ])

    assert result["total_centavos"] is None
    assert result["known_subtotal_centavos"] == 1400
    assert result["total_is_complete"] is False
    assert result["status"] == "unavailable"
    assert result["per_leg"][1]["reason"] == reason


def test_unavailable_leg_does_not_contribute_a_stale_amount():
    result = summarise_fares([
        _ride("P-A", 1400),
        _ride("P-B", 1950, "unavailable", "No applicable fare rule."),
    ])

    assert result["total_centavos"] is None
    assert result["known_subtotal_centavos"] == 1400
    assert result["per_leg"][1]["amount_centavos"] is None
    assert result["per_leg"][1]["status"] == "unavailable"


def test_empty_rides_do_not_produce_a_free_journey():
    result = summarise_fares([])

    assert result["per_leg"] == []
    assert result["total_centavos"] is None
    assert result["known_subtotal_centavos"] == 0
    assert result["total_is_complete"] is False
    assert result["status"] == "unavailable"


def test_missing_classification_is_not_assumed_exact():
    ride = _ride("P-A", 1400)
    del ride["fare"]["status"]
    result = summarise_fares([ride])

    assert result["total_centavos"] is None
    assert result["known_subtotal_centavos"] == 0
    assert result["status"] == "unavailable"
    assert result["per_leg"][0]["reason"] == "No supported fare calculation."


def test_invalid_amounts_are_rejected_but_supported_zero_is_preserved():
    for amount in (None, -1, True, 19.5, "1400", float("nan")):
        result = summarise_fares([_ride("P-A", amount)])

        assert result["total_centavos"] is None
        assert result["known_subtotal_centavos"] == 0
        assert result["status"] == "unavailable"

    result = summarise_fares([_ride("P-A", 0)])

    assert result["total_centavos"] == 0
    assert result["total_is_complete"] is True
    assert result["status"] == "exact"
