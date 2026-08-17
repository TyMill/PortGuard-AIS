"""Research orchestration for scene-level risk and runtime assurance."""

from dataclasses import dataclass
from time import perf_counter

from portguard_ais.assurance.config import ResearchAssuranceConfig
from portguard_ais.assurance.graph import build_scene_graph
from portguard_ais.assurance.models import (
    AssuredSceneDecision,
    SceneEvidence,
    SceneGraph,
    SceneRiskAssessment,
    SceneStateTransition,
)
from portguard_ais.assurance.scoring import assess_scene_risk, estimate_scene_evidence
from portguard_ais.assurance.supervisor import supervise_scene
from portguard_ais.assurance.temporal import SceneTemporalMonitor
from portguard_ais.config import PortGuardConfig
from portguard_ais.models import EncounterAssessment, VesselObservation
from portguard_ais.pipeline import PortGuardPipeline


@dataclass(frozen=True)
class ResearchSceneResult:
    """All outputs produced for one scene update."""

    pairwise_assessments: list[EncounterAssessment]
    graph: SceneGraph
    evidence: SceneEvidence
    risk: SceneRiskAssessment
    transition: SceneStateTransition
    decision: AssuredSceneDecision


class ResearchScenePipeline:
    """Compose PortGuard pairwise assessment with scene reasoning and assurance."""

    def __init__(
        self,
        portguard_config: PortGuardConfig | None = None,
        research_config: ResearchAssuranceConfig | None = None,
    ) -> None:
        self.base = PortGuardPipeline(portguard_config)
        self.config = research_config or ResearchAssuranceConfig()
        self.temporal = SceneTemporalMonitor(self.config.temporal)

    def reset(self) -> None:
        """Reset temporal state for independent scenario runs."""
        self.base.alerts.reset()
        self.temporal.reset()

    def process_snapshot(
        self,
        observations: list[VesselObservation],
        evidence: SceneEvidence | None = None,
    ) -> ResearchSceneResult:
        """Assess a same-timestamp multi-vessel snapshot and gate alert authority."""
        started = perf_counter()
        pairwise = self.base.process_snapshot(observations)
        if not pairwise:
            raise ValueError("research scene requires at least one candidate vessel encounter")
        graph = build_scene_graph(pairwise, self.config.scene_risk)
        measured_latency_ms = (perf_counter() - started) * 1000.0
        if evidence is None:
            resolved_evidence = estimate_scene_evidence(graph, latency_ms=measured_latency_ms)
        else:
            resolved_evidence = evidence
        risk = assess_scene_risk(graph, resolved_evidence, self.config.scene_risk)
        transition = self.temporal.update(risk)
        decision = supervise_scene(
            risk,
            transition,
            resolved_evidence,
            self.config.assurance,
        )
        return ResearchSceneResult(
            pairwise_assessments=pairwise,
            graph=graph,
            evidence=resolved_evidence,
            risk=risk,
            transition=transition,
            decision=decision,
        )
