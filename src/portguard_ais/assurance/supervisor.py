"""Runtime supervisor for scene-level decision-support authority."""

from portguard_ais.assurance.config import AssuranceConfig
from portguard_ais.assurance.models import (
    AssuredSceneDecision,
    AssuranceMode,
    DecisionAuthority,
    SceneEvidence,
    SceneRiskAssessment,
    SceneStateTransition,
)
from portguard_ais.enums import RiskLevel


def evidence_quality(evidence: SceneEvidence, config: AssuranceConfig) -> float:
    """Calculate bounded evidence quality from explicit degradation indicators."""
    latency_penalty = min(evidence.latency_ms / config.deadline_ms, 1.0)
    weighted_penalty = (
        config.missing_weight * evidence.missing_optional_fraction
        + config.stale_weight * evidence.stale_fraction
        + config.anomaly_weight * evidence.anomaly_fraction
        + config.coverage_weight * (1.0 - evidence.coverage_ratio)
        + config.latency_weight * latency_penalty
    )
    weight_sum = (
        config.missing_weight
        + config.stale_weight
        + config.anomaly_weight
        + config.coverage_weight
        + config.latency_weight
    )
    degradation = weighted_penalty / max(weight_sum, 1e-12)
    confidence_quality = (
        0.70 * evidence.mean_pairwise_confidence
        + 0.30 * (1.0 - evidence.low_confidence_edge_fraction)
    )
    quality = confidence_quality * (1.0 - degradation)
    return round(min(max(quality, 0.0), 1.0), 6)


def _nominal_authority(state: RiskLevel) -> DecisionAuthority:
    mapping = {
        RiskLevel.SAFE: DecisionAuthority.NO_ALERT,
        RiskLevel.WATCH: DecisionAuthority.ADVISORY,
        RiskLevel.WARNING: DecisionAuthority.WARNING,
        RiskLevel.CRITICAL: DecisionAuthority.CRITICAL,
    }
    return mapping[state]


def supervise_scene(
    assessment: SceneRiskAssessment,
    transition: SceneStateTransition,
    evidence: SceneEvidence,
    config: AssuranceConfig,
) -> AssuredSceneDecision:
    """Gate the authority of a scene-level output using runtime evidence quality."""
    quality = evidence_quality(evidence, config)
    hard_fallback = (
        evidence.stale_fraction >= config.fallback_stale_fraction
        or evidence.coverage_ratio <= config.fallback_coverage_ratio
        or evidence.latency_ms > config.deadline_ms
        or quality <= config.fallback_quality_threshold
    )

    rationale = [
        *assessment.rationale,
        f"temporal scene state={transition.current_state.value}",
        f"evidence quality={quality:.3f}",
    ]

    if hard_fallback:
        rationale.append("runtime assurance selected fallback due to insufficient evidence")
        return AssuredSceneDecision(
            timestamp=assessment.timestamp,
            scene_state=transition.current_state,
            assurance_mode=AssuranceMode.FALLBACK,
            authority=DecisionAuthority.FALLBACK,
            evidence_quality=quality,
            emitted_risk_score=None,
            rationale=tuple(rationale),
        )

    if quality <= config.human_verify_quality_threshold:
        rationale.append("automated alert authority withheld; human verification required")
        return AssuredSceneDecision(
            timestamp=assessment.timestamp,
            scene_state=transition.current_state,
            assurance_mode=AssuranceMode.HUMAN_VERIFY,
            authority=DecisionAuthority.HUMAN_VERIFY,
            evidence_quality=quality,
            emitted_risk_score=assessment.conservative_upper_score,
            rationale=tuple(rationale),
        )

    authority = _nominal_authority(transition.current_state)
    if quality < config.degraded_quality_threshold:
        if authority == DecisionAuthority.CRITICAL:
            authority = DecisionAuthority.WARNING
        elif authority == DecisionAuthority.WARNING:
            authority = DecisionAuthority.ADVISORY
        rationale.append("decision-support authority capped because evidence is degraded")
        mode = AssuranceMode.DEGRADED
    else:
        rationale.append("runtime evidence supports nominal decision authority")
        mode = AssuranceMode.NOMINAL

    return AssuredSceneDecision(
        timestamp=assessment.timestamp,
        scene_state=transition.current_state,
        assurance_mode=mode,
        authority=authority,
        evidence_quality=quality,
        emitted_risk_score=assessment.scene_risk_score,
        rationale=tuple(rationale),
    )
