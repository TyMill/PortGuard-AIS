"""Multi-seed robustness and ablation campaign for the JMSE assurance study."""

import csv
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, stdev

from portguard_ais.assurance.config import ResearchAssuranceConfig
from portguard_ais.evaluation.jmse_benchmark import JMSEBenchmarkResult, run_jmse_benchmark
from portguard_ais.evaluation.jmse_robustness import jitter_scenarios
from portguard_ais.evaluation.jmse_scenarios import jmse_scenarios


@dataclass(frozen=True)
class CampaignRow:
    seed: int
    variant: str
    method: str
    precision: float
    recall: float
    f1: float
    false_alert_rate: float
    alert_transitions: int
    degraded_input_detection_rate: float
    overconfident_critical_rate: float
    inappropriate_intervention_rate: float
    authority_capped_steps: int
    human_verify_steps: int
    fallback_steps: int


@dataclass(frozen=True)
class AggregateRow:
    variant: str
    method: str
    metric: str
    n: int
    mean: float
    std: float
    ci95_low: float
    ci95_high: float


def research_variants() -> dict[str, ResearchAssuranceConfig]:
    full = ResearchAssuranceConfig()
    return {
        "FULL": full,
        "NO_COUPLING": full.model_copy(
            update={"scene_risk": full.scene_risk.model_copy(update={"coupling_weight": 0.0})}
        ),
        "NO_PERSISTENCE": full.model_copy(
            update={
                "temporal": full.temporal.model_copy(
                    update={"persistence_updates": 1, "resolving_updates": 1}
                )
            }
        ),
        "NO_HYSTERESIS": full.model_copy(
            update={"temporal": full.temporal.model_copy(update={"release_margin": 0.0})}
        ),
    }


def _alert_transitions(result: JMSEBenchmarkResult, field: str) -> int:
    previous_by_scenario: dict[str, bool] = {}
    transitions = 0
    for record in result.records:
        current = bool(getattr(record, field))
        previous = previous_by_scenario.get(record.scenario)
        if previous is not None and current != previous:
            transitions += 1
        previous_by_scenario[record.scenario] = current
    return transitions


def _campaign_rows(seed: int, variant: str, result: JMSEBenchmarkResult) -> list[CampaignRow]:
    method_fields = {
        "B0_CPA_TCPA": "b0_cpa_tcpa",
        "B1_PAIRWISE_STATIC": "b1_pairwise_static",
        "B2_PAIRWISE_TEMPORAL": "b2_pairwise_temporal",
        "B3_SCENE_STATIC": "b3_scene_static",
        "B4_SCENE_TEMPORAL": "b4_scene_temporal",
        "OURS_ASSURED_OUTPUT": "ours_assured",
    }
    return [
        CampaignRow(
            seed=seed,
            variant=variant,
            method=item.method,
            precision=item.precision,
            recall=item.recall,
            f1=item.f1,
            false_alert_rate=item.false_alert_rate,
            alert_transitions=_alert_transitions(result, method_fields[item.method]),
            degraded_input_detection_rate=result.assurance.degraded_input_detection_rate,
            overconfident_critical_rate=result.assurance.overconfident_critical_rate,
            inappropriate_intervention_rate=result.assurance.inappropriate_intervention_rate,
            authority_capped_steps=result.assurance.authority_capped_steps,
            human_verify_steps=result.assurance.human_verify_steps,
            fallback_steps=result.assurance.fallback_steps,
        )
        for item in result.methods
    ]


def run_jmse_campaign(
    *,
    seed_count: int = 30,
    base_seed: int = 20260817,
    steps: int = 18,
    interval_seconds: int = 30,
    position_jitter_nm: float = 0.08,
) -> tuple[CampaignRow, ...]:
    """Run stochastic geometry robustness and registered ablations.

    For every seed the canonical scenario templates are regenerated and then perturbed by
    one fixed local-plane offset per vessel trajectory. This produces coherent alternative
    relative geometries without injecting frame-to-frame measurement noise. The same seeded
    scenario ensemble is reused across ablation variants for paired comparison.
    """
    if seed_count < 2:
        raise ValueError("seed_count must be at least 2")
    if position_jitter_nm < 0.0:
        raise ValueError("position_jitter_nm must be non-negative")

    rows: list[CampaignRow] = []
    for offset in range(seed_count):
        seed = base_seed + offset
        canonical = jmse_scenarios(
            steps=steps,
            interval_seconds=interval_seconds,
            seed=seed,
        )
        perturbed = jitter_scenarios(
            canonical,
            seed=seed,
            position_jitter_nm=position_jitter_nm,
        )
        for variant, config in research_variants().items():
            result = run_jmse_benchmark(
                steps=steps,
                interval_seconds=interval_seconds,
                seed=seed,
                research_config=config,
                scenarios=perturbed,
            )
            rows.extend(_campaign_rows(seed, variant, result))
    return tuple(rows)


def _aggregate(rows: tuple[CampaignRow, ...]) -> tuple[AggregateRow, ...]:
    metric_names = (
        "precision",
        "recall",
        "f1",
        "false_alert_rate",
        "alert_transitions",
        "degraded_input_detection_rate",
        "overconfident_critical_rate",
        "inappropriate_intervention_rate",
        "authority_capped_steps",
        "human_verify_steps",
        "fallback_steps",
    )
    groups: dict[tuple[str, str], list[CampaignRow]] = {}
    for row in rows:
        groups.setdefault((row.variant, row.method), []).append(row)

    output: list[AggregateRow] = []
    for (variant, method), items in sorted(groups.items()):
        for metric in metric_names:
            values = [float(getattr(item, metric)) for item in items]
            n = len(values)
            avg = mean(values)
            sd = stdev(values) if n > 1 else 0.0
            half = 1.96 * sd / math.sqrt(n) if n > 1 else 0.0
            output.append(
                AggregateRow(
                    variant=variant,
                    method=method,
                    metric=metric,
                    n=n,
                    mean=round(avg, 6),
                    std=round(sd, 6),
                    ci95_low=round(avg - half, 6),
                    ci95_high=round(avg + half, 6),
                )
            )
    return tuple(output)


def write_jmse_campaign(
    output_dir: str | Path,
    *,
    seed_count: int = 30,
    base_seed: int = 20260817,
    steps: int = 18,
    interval_seconds: int = 30,
    position_jitter_nm: float = 0.08,
) -> tuple[CampaignRow, ...]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = run_jmse_campaign(
        seed_count=seed_count,
        base_seed=base_seed,
        steps=steps,
        interval_seconds=interval_seconds,
        position_jitter_nm=position_jitter_nm,
    )
    aggregate = _aggregate(rows)

    with (output / "jmse_campaign_per_seed.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)

    with (output / "jmse_campaign_aggregate.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(aggregate[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in aggregate)

    payload = {
        "seed_count": seed_count,
        "base_seed": base_seed,
        "steps": steps,
        "interval_seconds": interval_seconds,
        "position_jitter_nm": position_jitter_nm,
        "variants": list(research_variants()),
        "interpretation": (
            "Each seed generates a coherent alternative relative geometry through a fixed "
            "trajectory-level vessel offset. Confidence intervals summarize controlled synthetic "
            "robustness to geometry perturbation; they are not estimates of real-world VTS accuracy."
        ),
        "aggregate": [asdict(row) for row in aggregate],
    }
    (output / "jmse_campaign_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return rows
