from datetime import UTC, datetime, timedelta

from portguard_ais.config import NearMissConfig
from portguard_ais.enums import EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    RelativeMotion,
    RiskComponents,
)
from portguard_ais.near_miss.miner import mine_near_misses


def _assessment(
    offset: int, score: float, dcpa: float, converging: bool = True
) -> EncounterAssessment:
    return EncounterAssessment(
        encounter_id="enc-x",
        timestamp=datetime(2026, 8, 3, 12, 0, tzinfo=UTC) + timedelta(seconds=offset),
        own_mmsi=1,
        target_mmsi=2,
        encounter_type=EncounterType.HEAD_ON,
        risk_level=RiskLevel.WARNING,
        risk_score=score,
        confidence=1.0,
        relative_motion=RelativeMotion(
            current_distance_nm=1,
            dcpa_nm=dcpa,
            tcpa_min=5,
            relative_speed_kn=10,
            closing_speed_kn=10,
            converging=converging,
            relative_bearing_deg=0,
            cpa_east_nm=0,
            cpa_north_nm=0,
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


def test_near_miss_is_ranked() -> None:
    events = mine_near_misses(
        [_assessment(0, 0.6, 0.3), _assessment(30, 0.8, 0.1)],
        NearMissConfig(),
    )
    assert len(events) == 1
    assert events[0].peak_risk_score == 0.8
    assert events[0].severity_rank > 0.0


def test_low_risk_is_excluded() -> None:
    events = mine_near_misses(
        [_assessment(0, 0.2, 0.1), _assessment(30, 0.2, 0.1)],
        NearMissConfig(),
    )
    assert events == []
