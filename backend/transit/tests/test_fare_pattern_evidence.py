"""Pattern evidence must be verified before a fare can be quoted."""
from datetime import date

import pytest

from transit.models import RouteEvidence
from transit.planner.fare_quotes import quote_leg_fare
from transit.planner.loader import load_network
from transit.tests.db_fixtures import build_verified_network


@pytest.mark.django_db
@pytest.mark.parametrize("allow_documented", [False, True])
@pytest.mark.parametrize("evidence_status", ["verified", "documented", None])
def test_pattern_evidence_controls_fares_without_hiding_patterns(
    allow_documented, evidence_status, django_assert_num_queries,
):
    fixture = build_verified_network()
    route_id = fixture["routes"]["A"].pk
    evidence = RouteEvidence.objects.filter(pattern__route_id=route_id)

    if evidence_status is None:
        evidence.delete()
    else:
        evidence.update(status=evidence_status)

    network = load_network(
        allow_documented=allow_documented, use_cache=False,
    )
    pattern = next(
        p for p in network.patterns if p.route_id == str(route_id)
    )

    # A verified-labelled pattern remains loaded in either mode.
    # This correction changes fare eligibility, not journey visibility.
    assert pattern.status == "verified"
    assert pattern.has_verified_evidence is (evidence_status == "verified")

    expected_sources = (
        (str(fixture["src"].pk),)
        if evidence_status == "verified"
        or (allow_documented and evidence_status == "documented")
        else ()
    )
    assert pattern.evidence_source_ids == expected_sources

    # The decision uses the loaded network, with no query per fare quote.
    with django_assert_num_queries(0):
        quote = quote_leg_fare(
            network,
            pattern=pattern,
            distance_m=3000,
            passenger_category="regular",
            on=date(2026, 10, 21),
        )

    if evidence_status == "verified":
        assert quote.amount_centavos == 1300
        assert quote.status == "exact"
        assert quote.reason is None
    else:
        assert quote.amount_centavos is None
        assert quote.status == "unavailable"
        assert quote.reason == "Route verification is incomplete."