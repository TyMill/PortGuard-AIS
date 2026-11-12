"""Regression tests for separate candidate near-miss episodes."""

from datetime import UTC, datetime, timedelta

from portguard_ais.config import NearMissConfig
from portguard_ais.enums import EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    GeoPoint,
    RelativeMotion,
    RiskComponents,
)
from portguard_ais.near_miss.episodes import segment_near_miss_episodes


def _assessment(
    seconds: int,
    *,
    score: float = 0.8,
    dcpa: float = 0.1,
    tcpa: float = 5.0,
    converging: bool = True,
) -> EncounterAssessment:
    return EncounterAssessment(
        encounter_id="enc-fixed-pair",
        timestamp=datetime(2026, 8, 3, 12, tzinfo=UTC) + timedelta(seconds=seconds),
        own_mmsi=123,
        target_mmsi=456,
        encounter_type=EncounterType.HEAD_ON,
        risk_level=RiskLevel.WARNING,
        risk_score=score,
        confidence=1.0,
        own_position=GeoPoint(lat=53.5, lon=14.5),
        target_position=GeoPoint(lat=53.6, lon=14.6),
        relative_motion=RelativeMotion(
            current_distance_nm=0.6,
            dcpa_nm=dcpa,
            tcpa_min=tcpa,
            relative_speed_kn=10.0,
            closing_speed_kn=9.0,
            converging=converging,
            relative_bearing_deg=0.0,
            cpa_east_nm=0.0,
            cpa_north_nm=0.0,
        ),
        domain=DomainAssessment(
            forward_nm=0.5,
            aft_nm=0.2,
            lateral_nm=0.2,
            normalized_distance=0.5,
            violated=True,
        ),
        colreg=ColregContext(
            rule="Rule 14",
            own_role=VesselRole.MUTUAL_ACTION,
            target_role=VesselRole.MUTUAL_ACTION,
            explanation="test",
        ),
        components=RiskComponents(dcpa=1, tcpa=1, range=1, closing_speed=1, domain=1),
        rationale=("test",),
    )


def test_split_repeated_encounters_by_long_gap() -> None:
    events = segment_near_miss_episodes(
        [_assessment(0), _assessment(30), _assessment(3600), _assessment(3630)],
        NearMissConfig(),
    )
    assert len(events) == 2
    assert events[0].ended_at < events[1].started_at
    assert events[0].episode_id != events[1].episode_id


def test_split_on_intervening_nonhazardous_update() -> None:
    events = segment_near_miss_episodes(
        [
            _assessment(0),
            _assessment(30),
            _assessment(60, score=0.1),
            _assessment(90),
            _assessment(120),
        ],
        NearMissConfig(),
    )
    assert len(events) == 2


def test_no_cross_timestamp_predicate_mixing() -> None:
    events = segment_near_miss_episodes(
        [
            _assessment(0, score=0.9, dcpa=0.9),
            _assessment(30, score=0.1, dcpa=0.1),
        ],
        NearMissConfig(),
    )
    assert events == []


def test_no_nonconverging_false_episode() -> None:
    assert segment_near_miss_episodes(
        [_assessment(0, converging=False), _assessment(30, converging=False)],
        NearMissConfig(),
    ) == []


def test_no_zero_tcpa_false_episode() -> None:
    assert segment_near_miss_episodes(
        [_assessment(0, tcpa=0), _assessment(30, tcpa=0)],
        NearMissConfig(),
    ) == []


def test_duplicate_timestamp_does_not_satisfy_minimum_observations() -> None:
    events = segment_near_miss_episodes(
        [_assessment(0), _assessment(0), _assessment(30, score=0.1)],
        NearMissConfig(),
    )
    assert events == []


def test_midpoint_of_peak_risk_is_reported() -> None:
    events = segment_near_miss_episodes(
        [_assessment(0, score=0.6), _assessment(30, score=0.9)],
        NearMissConfig(),
    )
    assert len(events) == 1
    assert events[0].midpoint_lat == 53.55
    assert events[0].midpoint_lon == 14.55
    assert events[0].observation_count == 2


def test_reject_nonpositive_gap() -> None:
    import pytest

    with pytest.raises(ValueError, match="max_gap_seconds"):
        segment_near_miss_episodes([], NearMissConfig(), max_gap_seconds=0)
