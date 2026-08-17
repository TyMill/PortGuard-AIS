"""Interpretable scene-level risk and uncertainty scoring."""

from portguard_ais.assurance.config import SceneRiskConfig
from portguard_ais.assurance.models import SceneEvidence, SceneGraph, SceneRiskAssessment


def estimate_scene_evidence(graph: SceneGraph, *, latency_ms: float = 0.0) -> SceneEvidence:
    """Derive default assurance evidence from a scene graph."""
    mean_confidence = (
        sum(edge.confidence for edge in graph.edges) / len(graph.edges) if graph.edges else 1.0
    )
    return SceneEvidence(
        mean_pairwise_confidence=round(mean_confidence, 6),
        low_confidence_edge_fraction=graph.low_confidence_edge_fraction,
        latency_ms=latency_ms,
    )


def uncertainty_score(evidence: SceneEvidence) -> float:
    """Return a bounded uncertainty score from scene evidence."""
    confidence_loss = 1.0 - evidence.mean_pairwise_confidence
    coverage_loss = 1.0 - evidence.coverage_ratio
    value = (
        0.30 * confidence_loss
        + 0.20 * evidence.low_confidence_edge_fraction
        + 0.20 * evidence.stale_fraction
        + 0.10 * evidence.missing_optional_fraction
        + 0.10 * evidence.anomaly_fraction
        + 0.10 * coverage_loss
    )
    return round(min(max(value, 0.0), 1.0), 6)


def assess_scene_risk(
    graph: SceneGraph,
    evidence: SceneEvidence,
    config: SceneRiskConfig,
) -> SceneRiskAssessment:
    """Aggregate pairwise hazard and graph coupling into an explainable scene score."""
    risks = sorted((edge.risk_score for edge in graph.edges), reverse=True)
    peak = risks[0] if risks else 0.0
    selected = risks[: config.top_k_edges]
    top_k_mean = sum(selected) / len(selected) if selected else 0.0
    total_weight = config.peak_weight + config.top_k_weight + config.coupling_weight
    hazard = (
        peak * config.peak_weight
        + top_k_mean * config.top_k_weight
        + graph.coupling_score * config.coupling_weight
    ) / total_weight
    uncertainty = uncertainty_score(evidence)
    conservative_upper = min(hazard + config.uncertainty_upper_weight * uncertainty, 1.0)
    rationale = (
        f"peak pairwise risk={peak:.3f}",
        f"top-{len(selected)} mean risk={top_k_mean:.3f}",
        f"scene coupling={graph.coupling_score:.3f}",
        f"evidence uncertainty={uncertainty:.3f}",
        f"conservative upper risk={conservative_upper:.3f}",
    )
    return SceneRiskAssessment(
        timestamp=graph.timestamp,
        peak_pairwise_risk=round(peak, 6),
        top_k_mean_risk=round(top_k_mean, 6),
        coupling_score=graph.coupling_score,
        scene_risk_score=round(hazard, 6),
        uncertainty_score=uncertainty,
        conservative_upper_score=round(conservative_upper, 6),
        rationale=rationale,
    )
