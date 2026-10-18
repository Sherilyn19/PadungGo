"""Model constraint and validation tests (SQLite lite mode)."""
from datetime import date, datetime, timezone

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from transit.models import (
    DataSource,
    FareRule,
    PatternStop,
    Route,
    RoutePattern,
    Stop,
    TransferConnection,
)
from transit.models.enums import (
    FarePolicyKind,
    PatternDirection,
    RecordStatus,
    VehicleClass,
)
from transit.models.fares import validate_fare_policy

pytestmark = pytest.mark.django_db


def _source():
    return DataSource.objects.create(
        title="Test source", collected_at=datetime(2026, 1, 1, tzinfo=timezone.utc)
    )


def _stop(name, lat=10.3, lon=123.9):
    return Stop.objects.create(name=name, latitude=lat, longitude=lon)


def test_pattern_sequence_unique():
    route = Route.objects.create(code="S1", vehicle_class=VehicleClass.JEEPNEY)
    pat = RoutePattern.objects.create(
        route=route, variant_key="main", direction=PatternDirection.OUTBOUND
    )
    s1, s2 = _stop("A"), _stop("B")
    PatternStop.objects.create(pattern=pat, stop=s1, sequence=0)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            PatternStop.objects.create(pattern=pat, stop=s2, sequence=0)


def test_pattern_stop_may_repeat_on_loop():
    route = Route.objects.create(code="LP", vehicle_class=VehicleClass.JEEPNEY)
    pat = RoutePattern.objects.create(
        route=route, variant_key="loop", direction=PatternDirection.LOOP
    )
    s1 = _stop("Hub")
    PatternStop.objects.create(pattern=pat, stop=s1, sequence=0)
    # Same physical stop, later occurrence -> allowed.
    PatternStop.objects.create(pattern=pat, stop=s1, sequence=5)
    assert PatternStop.objects.filter(pattern=pat, stop=s1).count() == 2


def test_route_variant_unique():
    route = Route.objects.create(code="01K", vehicle_class=VehicleClass.JEEPNEY)
    RoutePattern.objects.create(route=route, variant_key="out", direction=PatternDirection.OUTBOUND)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RoutePattern.objects.create(route=route, variant_key="out", direction=PatternDirection.INBOUND)


def test_same_stop_reboarding_transfer_allowed_once():
    s1 = _stop("X")
    TransferConnection.objects.create(from_stop=s1, to_stop=s1, distance_m=0)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            TransferConnection.objects.create(from_stop=s1, to_stop=s1, distance_m=0)


def test_fare_rule_rejects_both_route_and_pattern():
    src = _source()
    route = Route.objects.create(code="R", vehicle_class=VehicleClass.JEEPNEY)
    pat = RoutePattern.objects.create(route=route, variant_key="v", direction=PatternDirection.OUTBOUND)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareRule.objects.create(
                vehicle_class=VehicleClass.JEEPNEY,
                route=route,
                pattern=pat,
                kind=FarePolicyKind.FLAT,
                policy={"amount_centavos": 1300},
                valid_from=date(2026, 1, 1),
                source=src,
            )


def test_fare_rule_date_range_constraint():
    src = _source()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            FareRule.objects.create(
                vehicle_class=VehicleClass.JEEPNEY,
                kind=FarePolicyKind.FLAT,
                policy={"amount_centavos": 1300},
                valid_from=date(2026, 6, 1),
                valid_until=date(2026, 1, 1),
                source=src,
            )


def test_fare_specificity_ordering():
    src = _source()
    route = Route.objects.create(code="R2", vehicle_class=VehicleClass.JEEPNEY)
    pat = RoutePattern.objects.create(route=route, variant_key="v", direction=PatternDirection.OUTBOUND)
    by_class = FareRule(vehicle_class=VehicleClass.JEEPNEY, kind=FarePolicyKind.FLAT,
                        policy={"amount_centavos": 1300}, valid_from=date(2026, 1, 1), source=src)
    by_route = FareRule(vehicle_class=VehicleClass.JEEPNEY, route=route, kind=FarePolicyKind.FLAT,
                        policy={"amount_centavos": 1300}, valid_from=date(2026, 1, 1), source=src)
    by_pattern = FareRule(vehicle_class=VehicleClass.JEEPNEY, pattern=pat, kind=FarePolicyKind.FLAT,
                          policy={"amount_centavos": 1300}, valid_from=date(2026, 1, 1), source=src)
    assert by_class.specificity == 0
    assert by_route.specificity == 1
    assert by_pattern.specificity == 2


def test_validate_fare_policy_flat_and_band():
    validate_fare_policy(FarePolicyKind.FLAT, {"amount_centavos": 1300})
    validate_fare_policy(
        FarePolicyKind.DISTANCE_BAND,
        {"base_centavos": 1300, "base_distance_m": 4000,
         "increment_centavos": 180, "increment_distance_m": 1000},
    )


def test_validate_fare_policy_rejects_bad():
    with pytest.raises(ValidationError):
        validate_fare_policy(FarePolicyKind.FLAT, {"amount_centavos": -1})
    with pytest.raises(ValidationError):
        validate_fare_policy(FarePolicyKind.FLAT, {})
    with pytest.raises(ValidationError):
        validate_fare_policy(FarePolicyKind.DISTANCE_BAND,
                             {"base_centavos": 1300, "base_distance_m": 4000,
                              "increment_centavos": 180, "increment_distance_m": 0})


def test_recordevidence_requires_exactly_one_target():
    src = _source()
    stop = _stop("Ev")
    ev = TransferConnection  # noqa: F841 (placeholder to keep import usage honest)
    from transit.models import RecordEvidence

    good = RecordEvidence(
        source=src, reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        reviewer="r", status="verified", stop=stop,
    )
    good.full_clean(exclude=None)  # should not raise on exactly-one target

    bad = RecordEvidence(
        source=src, reviewed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        reviewer="r", status="verified",
    )
    with pytest.raises(ValidationError):
        bad.clean()
