"""Transparent collision-risk component scoring."""

from portguard_ais.config import RiskThresholds, RiskWeights
from portguard_ais.enums import RiskLevel
from portguard_ais.models import DomainAssessment, RelativeMotion, RiskComponents


def _inverse_linear(value: float, limit: float) -> float:
    return min(max(1.0 - value / max(limit, 1e-9), 0.0), 1.0)


def compute_components(
    motion: RelativeMotion,
    domain: DomainAssessment,
    thresholds: RiskThresholds,
) -> RiskComponents:
    """Transform physical measures into bounded explainable components."""
    dcpa_limit = max(domain.forward_nm, domain.lateral_nm, 0.5)
    closing_limit = 20.0
    return RiskComponents(
        dcpa=_inverse_linear(motion.dcpa_nm, dcpa_limit),
        tcpa=_inverse_linear(motion.tcpa_min, thresholds.tcpa_horizon_min)
        if motion.converging
        else 0.0,
        range=_inverse_linear(motion.current_distance_nm, thresholds.close_range_nm),
        closing_speed=min(motion.closing_speed_kn / closing_limit, 1.0),
        domain=1.0 if domain.violated else _inverse_linear(domain.normalized_distance, 3.0),
    )


def aggregate_risk(components: RiskComponents, weights: RiskWeights) -> float:
    """Return normalized weighted risk in [0, 1]."""
    weighted = (
        components.dcpa * weights.dcpa
        + components.tcpa * weights.tcpa
        + components.range * weights.range
        + components.closing_speed * weights.closing_speed
        + components.domain * weights.domain
    )
    return round(weighted / weights.total, 6)


def classify_risk(score: float, thresholds: RiskThresholds) -> RiskLevel:
    """Map a risk score to the configured severity level."""
    if score >= thresholds.critical:
        return RiskLevel.CRITICAL
    if score >= thresholds.warning:
        return RiskLevel.WARNING
    if score >= thresholds.watch:
        return RiskLevel.WATCH
    return RiskLevel.SAFE
