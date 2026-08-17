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
    degraded_input: bool
    vessel_count: int
    edge_count: int
    peak_pairwise_risk: float
    scene_risk: float
    scene_coupling: float
    evidence_quality_mode: str
    assurance_authority: str
    assurance_intervened: bool
    hazard_state_detected: bool
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
    """Assurance-specific benchmark counters and rates."""

    degraded_steps: int
    degraded_steps_detected: int
    degraded_input_detection_rate: float
    human_verify_steps: int
    fallback_steps: int
    authority_capped_steps: int
    overconfident_critical_steps: int
    overconfident_critical_rate: float
    inappropriate_intervention_steps: int
    inappropriate_intervention_rate: float
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
    """Return whether the operational output asks an operator to act or verify."""
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
    scenarios: tuple[JMSEScenario, ...] | None = None,
) -> JMSEBenchmarkResult:
    """Run controlled JMSE scenarios across progressive baselines."""
    base_config = portguard_config or PortGuardConfig()
    research = research_config or ResearchAssuranceConfig()
    records: list[JMSEStepRecord] = []
    scenario_suite = scenarios or jmse_scenarios(
        steps=steps,
        interval_seconds=interval_seconds,
        seed=seed,
    )

    for scenario in scenario_suite:
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
            decision = supervise_scene(scene, scene_transition, evidence, research.assurance)

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
            degraded = _is_degraded_scenario_step(scenario, step)
            intervened = decision.assurance_mode != AssuranceMode.NOMINAL

            records.append(
                JMSEStepRecord(
                    scenario=scenario.name,
                    step=step,
                    expected_hazard=step in scenario.hazardous_steps,
                    degraded_input=degraded,
                    vessel_count=len(graph.vessels),
                    edge_count=len(graph.edges),
                    peak_pairwise_risk=scene.peak_pairwise_risk,
                    scene_risk=scene.scene_risk_score,
                    scene_coupling=scene.coupling_score,
                    evidence_quality_mode=decision.assurance_mode.value,
                    assurance_authority=decision.authority.value,
                    assurance_intervened=intervened,
                    hazard_state_detected=b4,
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
        ("OURS_ASSURED_OUTPUT", "ours_assured"),
    )
    methods = tuple(
        _binary_summary(
            method,
            binary_alert_metrics(expected, [bool(getattr(record, field)) for record in records]),
        )
        for method, field in method_fields
    )

    degraded_records = [record for record in records if record.degraded_input]
    nominal_records = [record for record in records if not record.degraded_input]
    degraded_steps = len(degraded_records)
    degraded_detected = sum(record.assurance_intervened for record in degraded_records)
    overconfident = sum(
        record.assurance_authority == DecisionAuthority.CRITICAL.value
        for record in degraded_records
    )
    inappropriate_intervention = sum(record.assurance_intervened for record in nominal_records)
    inappropriate_fallback = sum(record.fallback for record in nominal_records)
    authority_capped = sum(
        record.evidence_quality_mode == AssuranceMode.DEGRADED.value for record in records
    )
    assurance = AssuranceSummary(
        degraded_steps=degraded_steps,
        degraded_steps_detected=degraded_detected,
        degraded_input_detection_rate=round(
            degraded_detected / degraded_steps if degraded_steps else 0.0, 6
        ),
        human_verify_steps=sum(record.human_verify for record in records),
        fallback_steps=sum(record.fallback for record in records),
        authority_capped_steps=authority_capped,
        overconfident_critical_steps=overconfident,
        overconfident_critical_rate=round(
            overconfident / degraded_steps if degraded_steps else 0.0, 6
        ),
        inappropriate_intervention_steps=inappropriate_intervention,
        inappropriate_intervention_rate=round(
            inappropriate_intervention / len(nominal_records) if nominal_records else 0.0, 6
        ),
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
    result = run_jmse_benchmark(steps=steps, interval_seconds=interval_seconds, seed=seed)

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
        "metric_interpretation": {
            "B4_SCENE_TEMPORAL": (
                "Pure scene-hazard detection after temporal filtering; this is the hazard-state "
                "component of the proposed system before assurance authority gating."
            ),
            "OURS_ASSURED_OUTPUT": (
                "Operational alert/verification output after runtime assurance. FALLBACK withholds "
                "an automated hazard statement and must not be interpreted as a detector miss "
                "without consulting hazard_state_detected."
            ),
        },
        "controlled_benchmark_notice": (
            "These are controlled synthetic mechanism-verification results, not claims of "
            "real-world VTS accuracy or certified navigation safety."
        ),
    }
    (output / "jmse_benchmark_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result
