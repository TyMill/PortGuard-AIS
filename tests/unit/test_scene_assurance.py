from datetime import UTC, datetime

from portguard_ais.assurance.config import AssuranceConfig, SceneRiskConfig, SceneTemporalConfig
from portguard_ais.assurance.graph import build_scene_graph
from portguard_ais.assurance.models import (
    AssuranceMode,
    DecisionAuthority,
    SceneEvidence,
    SceneRiskAssessment,
    SceneStateTransition,
)
from portguard_ais.assurance.scoring import assess_scene_risk
from portguard_ais.assurance.supervisor import supervise_scene
from portguard_ais.assurance.temporal import SceneTemporalMonitor
from portguard_ais.enums import EncounterType, RiskLevel, VesselRole
from portguard_ais.models import (
    ColregContext,
    DomainAssessment,
    EncounterAssessment,
    RelativeMotion,
    RiskComponents,
)


NOW = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)


def _assessment(own: int, target: int, score: float, confidence: float = 1.0) -> EncounterAssessment:
    if score >= 0.75:
        level = RiskLevel.CRITICAL
    elif score >= 0.50:
        level = RiskLevel.WARNING
    elif score >= 0.25:
        level = RiskLevel.WATCH
    else:
        level = RiskLevel.SAFE
    return EncounterAssessment(
        encounter_id=f"enc-{min(own, target)}-{max(own, target)}",
        timestamp=NOW,
        own_mmsi=own,
        target_mmsi=target,
        encounter_type=EncounterType.CROSSING_STARBOARD,
        risk_level=level,
        risk_score=score,
        confidence=confidence,
        relative_motion=RelativeMotion(
            current_distance_nm=1.0,
            dcpa_nm=0.1,
            tcpa_min=5.0,
            relative_speed_kn=10.0,
            closing_speed_kn=5.0,
            converging=True,
            relative_bearing_deg=45.0,
            cpa_east_nm=0.0,
            cpa_north_nm=0.0,
        ),
        domain=DomainAssessment(
            forward_nm=0.5,
            aft_nm=0.2,
            lateral_nm=0.2,
            normalized_distance=0.5,
            violated=score >= 0.5,
        ),
        colreg=ColregContext(
            rule="Rule 15",
            own_role=VesselRole.GIVE_WAY,
            target_role=VesselRole.STAND_ON,
            explanation="test",
        ),
        components=RiskComponents(
            dcpa=score,
            tcpa=score,
            range=score,
            closing_speed=score,
            domain=score,
        ),
        rationale=("test",),
    )


def _scene_risk(score: float) -> SceneRiskAssessment:
    return SceneRiskAssessment(
        timestamp=NOW,
        peak_pairwise_risk=score,
        top_k_mean_risk=score,
        coupling_score=0.5,
        scene_risk_score=score,
        uncertainty_score=0.0,
        conservative_upper_score=score,
        rationale=("test scene",),
    )


def _transition(state: RiskLevel) -> SceneStateTransition:
    return SceneStateTransition(
        timestamp=NOW,
        previous_state=state,
        current_state=state,
        changed=False,
        event="stable",
    )


def test_weighted_scene_graph_captures_three_vessel_coupling() -> None:
    assessments = [
        _assessment(1, 2, 0.80),
        _assessment(2, 3, 0.70),
        _assessment(1, 3, 0.10),
    ]
    graph = build_scene_graph(assessments, SceneRiskConfig())
    assert graph.vessels == (1, 2, 3)
    assert graph.conflict_components == ((1, 2, 3),)
    assert graph.maximum_component_size == 3
    assert graph.weighted_degree[2] == 1.5
    assert graph.coupling_score > 0.7


def test_scene_risk_combines_peak_top_k_and_coupling() -> None:
    graph = build_scene_graph(
        [_assessment(1, 2, 0.80), _assessment(2, 3, 0.70), _assessment(1, 3, 0.10)],
        SceneRiskConfig(),
    )
    evidence = SceneEvidence(mean_pairwise_confidence=1.0, low_confidence_edge_fraction=0.0)
    result = assess_scene_risk(graph, evidence, SceneRiskConfig())
    assert 0.0 < result.scene_risk_score < 1.0
    assert result.scene_risk_score > result.top_k_mean_risk * 0.5
    assert result.conservative_upper_score == result.scene_risk_score


def test_temporal_monitor_requires_persistent_critical_scene() -> None:
    monitor = SceneTemporalMonitor(SceneTemporalConfig(persistence_updates=2))
    first = monitor.update(_scene_risk(0.80))
    second = monitor.update(_scene_risk(0.80))
    assert first.current_state == RiskLevel.SAFE
    assert first.event == "pending-critical"
    assert second.current_state == RiskLevel.CRITICAL
    assert second.changed is True


def test_nominal_critical_scene_retains_critical_authority() -> None:
    decision = supervise_scene(
        _scene_risk(0.85),
        _transition(RiskLevel.CRITICAL),
        SceneEvidence(mean_pairwise_confidence=1.0, low_confidence_edge_fraction=0.0),
        AssuranceConfig(),
    )
    assert decision.assurance_mode == AssuranceMode.NOMINAL
    assert decision.authority == DecisionAuthority.CRITICAL


def test_low_confidence_critical_scene_requires_human_verification() -> None:
    decision = supervise_scene(
        _scene_risk(0.85),
        _transition(RiskLevel.CRITICAL),
        SceneEvidence(mean_pairwise_confidence=0.50, low_confidence_edge_fraction=1.0),
        AssuranceConfig(),
    )
    assert decision.assurance_mode == AssuranceMode.HUMAN_VERIFY
    assert decision.authority == DecisionAuthority.HUMAN_VERIFY
    assert decision.emitted_risk_score == 0.85


def test_degraded_evidence_caps_critical_authority() -> None:
    decision = supervise_scene(
        _scene_risk(0.85),
        _transition(RiskLevel.CRITICAL),
        SceneEvidence(mean_pairwise_confidence=0.80, low_confidence_edge_fraction=0.50),
        AssuranceConfig(),
    )
    assert decision.assurance_mode == AssuranceMode.DEGRADED
    assert decision.authority == DecisionAuthority.WARNING


def test_stale_scene_forces_fallback() -> None:
    decision = supervise_scene(
        _scene_risk(0.90),
        _transition(RiskLevel.CRITICAL),
        SceneEvidence(
            mean_pairwise_confidence=0.95,
            low_confidence_edge_fraction=0.0,
            stale_fraction=0.80,
        ),
        AssuranceConfig(),
    )
    assert decision.assurance_mode == AssuranceMode.FALLBACK
    assert decision.authority == DecisionAuthority.FALLBACK
    assert decision.emitted_risk_score is None


def test_low_scene_coverage_forces_fallback() -> None:
    decision = supervise_scene(
        _scene_risk(0.80),
        _transition(RiskLevel.WARNING),
        SceneEvidence(
            mean_pairwise_confidence=0.95,
            low_confidence_edge_fraction=0.0,
            coverage_ratio=0.40,
        ),
        AssuranceConfig(),
    )
    assert decision.assurance_mode == AssuranceMode.FALLBACK
