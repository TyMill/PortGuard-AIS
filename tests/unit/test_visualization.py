from datetime import UTC, datetime
from pathlib import Path

from portguard_ais.enums import EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    RelativeMotion,
    RiskComponents,
)
from portguard_ais.visualization.plots import plot_risk_timeline


def test_plot_risk_timeline(tmp_path: Path) -> None:
    assessment = EncounterAssessment(
        encounter_id="enc-x",
        timestamp=datetime(2026, 8, 3, 12, 0, tzinfo=UTC),
        own_mmsi=1,
        target_mmsi=2,
        encounter_type=EncounterType.HEAD_ON,
        risk_level=RiskLevel.WARNING,
        risk_score=0.6,
        confidence=1.0,
        relative_motion=RelativeMotion(
            current_distance_nm=1,
            dcpa_nm=0.1,
            tcpa_min=5,
            relative_speed_kn=10,
            closing_speed_kn=10,
            converging=True,
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
    output = plot_risk_timeline([assessment], tmp_path / "risk.png")
    assert output.is_file()
