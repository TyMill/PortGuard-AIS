from portguard_ais.config import RiskThresholds, RiskWeights
from portguard_ais.enums import RiskLevel
from portguard_ais.models import DomainAssessment, RelativeMotion
from portguard_ais.risk.scoring import aggregate_risk, classify_risk, compute_components


def test_high_risk_components_score_high() -> None:
    motion = RelativeMotion(
        current_distance_nm=0.1,
        dcpa_nm=0.01,
        tcpa_min=2.0,
        relative_speed_kn=20.0,
        closing_speed_kn=20.0,
        converging=True,
        relative_bearing_deg=0.0,
        cpa_east_nm=0.0,
        cpa_north_nm=0.0,
    )
    domain = DomainAssessment(
        forward_nm=0.5,
        aft_nm=0.2,
        lateral_nm=0.2,
        normalized_distance=0.0,
        violated=True,
    )
    thresholds = RiskThresholds()
    score = aggregate_risk(compute_components(motion, domain, thresholds), RiskWeights())
    assert score > thresholds.critical
    assert classify_risk(score, thresholds) == RiskLevel.CRITICAL
