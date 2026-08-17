"""Controlled benchmark for JMSE scene-risk and runtime-assurance experiments."""

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from portguard_ais.alerts.state_machine import AlertStateMachine
from portguard_ais.assurance.config import ResearchAssuranceConfig
from portguard_ais.assurance.graph import build_scene_graph
from portguard_ais.assurance.models import AssuranceMode, DecisionAuthority
from portguard_ais.assurance.scoring import assess_scene_risk, estimate_scene_evidence
from portguard_ais.assurance.supervisor import supervise_scene
from portguard_ais.assurance.temporal import SceneTemporalMonitor
from portguard_ais.config import PortGuardConfig
from portguard_ais.enums import AlertState, RiskLevel
from portguard_ais.evaluation.jmse_scenarios import JMSEScenario, jmse_scenarios
from portguard_ais.evaluation.metrics import BinaryMetrics, binary_alert_metrics
from portguard_ais.pipeline import PortGuardPipeline


@dataclass(frozen=True)
class JMSEStepRecord:
    """One benchmark row for one scenario update."""

    scenario: str
    step: int
    expected_hazard: bool
    vessel_count: int
    edge_count: int
    peak_pairwise_risk: float
    scene_risk: float
    scene_coupling: float
    evidence_quality_mode: str
    assurance_authority: str
    b0_cpa_tcpa: bool
    b1_pairwise_static: bool
    b2_pairwise_temporal: bool
    b3_scene_static: bool
    b4_scene_temporal: bool
    ours_assured: bool
    human_verify: bool
    fallback: bool


@dataclass(frozen=True)
class MethodSummary:
    """Binary alert metrics for one benchmark method."""

    method: str
    precision: float
    recall: float
    f1: float
    false_alert_rate: float


@dataclass(frozen=True)
class AssuranceSummary:
    """Assurance-specific benchmark counters."""

    degraded_steps: int
    human_verify_steps: int
    fallback_steps: int
    overconfident_critical_steps: int
    inappropriate_fallback_steps: int


@dataclass(frozen=True)
class JMSEBenchmarkResult:
    """Complete controlled benchmark result."""

    records: tuple[JMSEStepRecord, ...]
    methods: tuple[MethodSummary, ...]
    assurance: AssuranceSummary


def _binary_summary(method: str, metrics: BinaryMetrics) -> MethodSummary:
    return MethodSummary(
        method=method,
        precision=round(metrics.precision, 6),
        recall=round(metrics.recall, 6),
        f1=round(metrics.f1, 6),
        false_alert_rate=round(metrics.false_alert_rate, 6),
    )


def _is_pairwise_temporal_alert(state: AlertState) -> bool:
    return state in {AlertState.WARNING, AlertState.CRITICAL}


def _is_scene_temporal_alert(state: RiskLevel) -> bool:
    return state in {RiskLevel.WARNING, RiskLevel.CRITICAL}


def _is_assured_alert(authority: DecisionAuthority) -> bool:
    return authority in {
        DecisionAuthority.WARNING,
        DecisionAuthority.CRITICAL,
        DecisionAuthority.HUMAN_VERIFY,
    }


def _is_degraded_scenario_step(scenario: JMSEScenario, step: int) -> bool:
    override = scenario.evidence_overrides[step]
    return any(
        (
            override.mean_pairwise_confidence is not None,
            override.low_confidence_edge_fraction is not None,
            override.stale_fraction > 0.0,
            override.missing_optional_fraction > 0.0,
            override.anomaly_fraction > 0.0,
            override.coverage_ratio < 1.0,
            override.latency_ms > 0.0,
        )
    )


def run_jmse_benchmark(
    *,
    steps: int = 18,
    interval_seconds: int = 30,
    seed: int = 20260817,
    portguard_config: PortGuardConfig | None = None,
    research_config: ResearchAssuranceConfig | None = None,
) -> JMSEBenchmarkResult:
    """Run all controlled JMSE scenarios across progressive baselines."""
    base_config = portguard_config or PortGuardConfig()
    research = research_config or ResearchAssuranceConfig()
    records: list[JMSEStepRecord] = []

    for scenario in jmse_scenarios(
        steps=steps,
        interval_seconds=interval_seconds,
        seed=seed,
    ):
        pairwise_pipeline = PortGuardPipeline(base_config)
        pairwise_temporal = AlertStateMachine(base_config.alerts, base_config.thresholds)
        scene_temporal = SceneTemporalMonitor(research.temporal)

        for step, snapshot_tuple in enumerate(scenario.snapshots):
            snapshot = list(snapshot_tuple)
            pairwise = pairwise_pipeline.process_snapshot(snapshot)
            if not pairwise:
                continue
            graph = build_scene_graph(pairwise, research.scene_risk)
            base_evidence = estimate_scene_evidence(graph)
            evidence = scenario.evidence_for_step(step, base_evidence)
            scene = assess_scene_risk(graph, evidence, research.scene_risk)
            scene_transition = scene_temporal.update(scene)
            decision = supervise_scene(
                scene,
                scene_transition,
                evidence,
                research.assurance,
            )

            pairwise_states = [
                pairwise_temporal.update(assessment).current_state for assessment in pairwise
            ]
            b0 = any(
                assessment.relative_motion.converging
                and assessment.relative_motion.dcpa_nm <= 0.5
                and assessment.relative_motion.tcpa_min <= 20.0
                for assessment in pairwise
            )
            b1 = any(
                assessment.risk_level in {RiskLevel.WARNING, RiskLevel.CRITICAL}
                for assessment in pairwise
            )
            b2 = any(_is_pairwise_temporal_alert(state) for state in pairwise_states)
            b3 = scene.scene_risk_score >= research.temporal.warning
            b4 = _is_scene_temporal_alert(scene_transition.current_state)
            ours = _is_assured_alert(decision.authority)

            records.append(
                JMSEStepRecord(
                    scenario=scenario.name,
                    step=step,
                    expected_hazard=step in scenario.hazardous_steps,
                    vessel_count=len(graph.vessels),
                    edge_count=len(graph.edges),
                    peak_pairwise_risk=scene.peak_pairwise_risk,
                    scene_risk=scene.scene_risk_score,
                    scene_coupling=scene.coupling_score,
                    evidence_quality_mode=decision.assurance_mode.value,
                    assurance_authority=decision.authority.value,
                    b0_cpa_tcpa=b0,
                    b1_pairwise_static=b1,
                    b2_pairwise_temporal=b2,
                    b3_scene_static=b3,
                    b4_scene_temporal=b4,
                    ours_assured=ours,
                    human_verify=decision.assurance_mode == AssuranceMode.HUMAN_VERIFY,
                    fallback=decision.assurance_mode == AssuranceMode.FALLBACK,
                )
            )

    expected = [record.expected_hazard for record in records]
    method_fields = (
        ("B0_CPA_TCPA", "b0_cpa_tcpa"),
        ("B1_PAIRWISE_STATIC", "b1_pairwise_static"),
        ("B2_PAIRWISE_TEMPORAL", "b2_pairwise_temporal"),
        ("B3_SCENE_STATIC", "b3_scene_static"),
        ("B4_SCENE_TEMPORAL", "b4_scene_temporal"),
        ("OURS_ASSURED", "ours_assured"),
    )
    methods = tuple(
        _binary_summary(
            method,
            binary_alert_metrics(
                expected,
                [bool(getattr(record, field)) for record in records],
            ),
        )
        for method, field in method_fields
    )

    scenario_map = {
        scenario.name: scenario
        for scenario in jmse_scenarios(
            steps=steps,
            interval_seconds=interval_seconds,
            seed=seed,
        )
    }
    degraded_steps = sum(
        _is_degraded_scenario_step(scenario_map[record.scenario], record.step)
        for record in records
    )
    overconfident = sum(
        _is_degraded_scenario_step(scenario_map[record.scenario], record.step)
        and record.assurance_authority == DecisionAuthority.CRITICAL.value
        for record in records
    )
    inappropriate_fallback = sum(
        (not _is_degraded_scenario_step(scenario_map[record.scenario], record.step))
        and record.fallback
        for record in records
    )
    assurance = AssuranceSummary(
        degraded_steps=degraded_steps,
        human_verify_steps=sum(record.human_verify for record in records),
        fallback_steps=sum(record.fallback for record in records),
        overconfident_critical_steps=overconfident,
        inappropriate_fallback_steps=inappropriate_fallback,
    )
    return JMSEBenchmarkResult(tuple(records), methods, assurance)


def write_jmse_benchmark(
    output_dir: str | Path,
    *,
    steps: int = 18,
    interval_seconds: int = 30,
    seed: int = 20260817,
) -> JMSEBenchmarkResult:
    """Run the controlled benchmark and write manuscript-oriented CSV/JSON outputs."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = run_jmse_benchmark(
        steps=steps,
        interval_seconds=interval_seconds,
        seed=seed,
    )

    with (output / "jmse_step_records.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(result.records[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(record) for record in result.records)

    with (output / "jmse_method_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(result.methods[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(item) for item in result.methods)

    payload = {
        "methods": [asdict(item) for item in result.methods],
        "assurance": asdict(result.assurance),
        "record_count": len(result.records),
        "scenario_count": len({record.scenario for record in result.records}),
        "steps": steps,
        "interval_seconds": interval_seconds,
        "seed": seed,
        "controlled_benchmark_notice": (
            "These are controlled synthetic mechanism-verification results, not claims of "
            "real-world VTS accuracy or certified navigation safety."
        ),
    }
    (output / "jmse_benchmark_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result
