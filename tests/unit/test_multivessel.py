from datetime import UTC, datetime

from portguard_ais.encounters.multivessel import conflict_clusters
from portguard_ais.enums import EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    RelativeMotion,
    RiskComponents,
)


def _assessment(own: int, target: int, level: RiskLevel) -> EncounterAssessment:
    return EncounterAssessment(
        encounter_id=f"{own}-{target}",
        timestamp=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        own_mmsi=own,
        target_mmsi=target,
        encounter_type=EncounterType.CROSSING_STARBOARD,
        risk_level=level,
        risk_score=0.8 if level == RiskLevel.CRITICAL else 0.2,
        confidence=1.0,
        relative_motion=RelativeMotion(
            current_distance_nm=1,
            dcpa_nm=0.1,
            tcpa_min=5,
            relative_speed_kn=10,
            closing_speed_kn=5,
            converging=True,
            relative_bearing_deg=45,
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
            rule="Rule 15",
            own_role=VesselRole.GIVE_WAY,
            target_role=VesselRole.STAND_ON,
            explanation="test",
        ),
        components=RiskComponents(dcpa=1, tcpa=1, range=1, closing_speed=1, domain=1),
        rationale=("test",),
    )


def test_three_vessel_cluster() -> None:
    assessments = [
        _assessment(1, 2, RiskLevel.CRITICAL),
        _assessment(2, 3, RiskLevel.WARNING),
        _assessment(4, 5, RiskLevel.SAFE),
    ]
    assert conflict_clusters(assessments) == [(1, 2, 3)]
