from datetime import UTC, datetime, timedelta

from portguard_ais.alerts.state_machine import AlertStateMachine
from portguard_ais.config import AlertConfig, RiskThresholds
from portguard_ais.enums import AlertState, EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    RelativeMotion,
    RiskComponents,
)


def _assessment(timestamp: datetime, score: float, level: RiskLevel) -> EncounterAssessment:
    return EncounterAssessment(
        encounter_id="enc-test",
        timestamp=timestamp,
        own_mmsi=1,
        target_mmsi=2,
        encounter_type=EncounterType.HEAD_ON,
        risk_level=level,
        risk_score=score,
        confidence=1.0,
        relative_motion=RelativeMotion(
            current_distance_nm=1.0,
            dcpa_nm=0.1,
            tcpa_min=5.0,
            relative_speed_kn=10.0,
            closing_speed_kn=10.0,
            converging=True,
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


def test_state_requires_persistence_and_then_closes() -> None:
    machine = AlertStateMachine(
        AlertConfig(persistence_updates=2, resolving_updates=2, cooldown_seconds=0),
        RiskThresholds(),
    )
    start = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)
    first = machine.update(_assessment(start, 0.8, RiskLevel.CRITICAL))
    second = machine.update(_assessment(start + timedelta(seconds=30), 0.8, RiskLevel.CRITICAL))
    resolving = machine.update(_assessment(start + timedelta(seconds=60), 0.1, RiskLevel.SAFE))
    closed = machine.update(_assessment(start + timedelta(seconds=90), 0.1, RiskLevel.SAFE))

    assert first.current_state == AlertState.SAFE
    assert not first.emitted
    assert second.current_state == AlertState.CRITICAL
    assert second.emitted
    assert resolving.current_state == AlertState.RESOLVING
    assert closed.current_state == AlertState.CLOSED
    assert closed.emitted
