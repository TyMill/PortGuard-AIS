"""Reproducible synthetic benchmark entry points."""

from dataclasses import asdict, dataclass

from portguard_ais.enums import AlertState
from portguard_ais.evaluation.synthetic import (
    ARTICLE_SCENARIOS,
    article_scenarios,
    synthetic_scenarios,
)
from portguard_ais.pipeline import PortGuardPipeline


@dataclass(frozen=True)
class SyntheticBenchmarkResult:
    """Compact legacy benchmark summary."""

    input_rows: int
    assessments: int
    emitted_alerts: int
    near_misses: int
    maximum_risk_score: float


@dataclass(frozen=True)
class ArticleScenarioResult:
    """Ground-truth-oriented summary of one SoftwareX scenario."""

    name: str
    own_mmsi: int
    target_mmsi: int
    expected_encounter: str
    expected_colreg_rule: str
    assessment_count: int
    converging_assessments: int
    expected_type_count: int
    classification_consistency: float
    observed_encounter_types: tuple[str, ...]
    peak_risk_score: float
    minimum_dcpa_nm: float
    minimum_converging_tcpa_min: float
    emitted_alerts: int
    first_emitted_state: str | None
    near_miss_detected: bool


@dataclass(frozen=True)
class ArticleBenchmarkResult:
    """Complete deterministic SoftwareX benchmark summary."""

    input_rows: int
    unique_vessels: int
    assessments: int
    emitted_alerts: int
    near_misses: int
    maximum_risk_score: float
    scenarios: tuple[ArticleScenarioResult, ...]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable nested representation."""
        return asdict(self)


def run_synthetic_benchmark(steps: int = 12) -> SyntheticBenchmarkResult:
    """Run the original deterministic scenarios through the complete pipeline."""
    if steps < 2:
        raise ValueError("steps must be at least 2")
    frame = synthetic_scenarios(steps=steps)
    result = PortGuardPipeline().process_frame(frame)
    return SyntheticBenchmarkResult(
        input_rows=len(frame),
        assessments=len(result.assessments),
        emitted_alerts=sum(alert.emitted for alert in result.alerts),
        near_misses=len(result.near_misses),
        maximum_risk_score=max(
            (assessment.risk_score for assessment in result.assessments),
            default=0.0,
        ),
    )


def run_article_benchmark(steps: int = 12, interval_seconds: int = 30) -> ArticleBenchmarkResult:
    """Run the isolated Rule 14/15/13 article suite through the full pipeline."""
    frame = article_scenarios(steps=steps, interval_seconds=interval_seconds)
    result = PortGuardPipeline().process_frame(frame)
    summaries: list[ArticleScenarioResult] = []

    near_miss_ids = {event.encounter_id for event in result.near_misses}

    for definition in ARTICLE_SCENARIOS:
        items = [
            item
            for item in result.assessments
            if item.own_mmsi == definition.own_mmsi and item.target_mmsi == definition.target_mmsi
        ]
        if not items:
            raise RuntimeError(f"No assessments produced for article scenario {definition.name}")

        encounter_id = items[0].encounter_id
        scenario_alerts = [alert for alert in result.alerts if alert.encounter_id == encounter_id]
        converging = [item for item in items if item.relative_motion.converging]
        expected_count = sum(
            item.encounter_type == definition.expected_encounter for item in converging
        )
        consistency = expected_count / len(converging) if converging else 0.0
        emitted = [alert for alert in scenario_alerts if alert.emitted]
        converging_tcpa = [item.relative_motion.tcpa_min for item in converging]

        summaries.append(
            ArticleScenarioResult(
                name=definition.name,
                own_mmsi=definition.own_mmsi,
                target_mmsi=definition.target_mmsi,
                expected_encounter=definition.expected_encounter.value,
                expected_colreg_rule=definition.expected_colreg_rule,
                assessment_count=len(items),
                converging_assessments=len(converging),
                expected_type_count=expected_count,
                classification_consistency=round(consistency, 6),
                observed_encounter_types=tuple(
                    sorted({item.encounter_type.value for item in items})
                ),
                peak_risk_score=max(item.risk_score for item in items),
                minimum_dcpa_nm=min(item.relative_motion.dcpa_nm for item in items),
                minimum_converging_tcpa_min=min(converging_tcpa, default=0.0),
                emitted_alerts=len(emitted),
                first_emitted_state=(
                    emitted[0].current_state.value if emitted else AlertState.SAFE.value
                ),
                near_miss_detected=encounter_id in near_miss_ids,
            )
        )

    return ArticleBenchmarkResult(
        input_rows=len(frame),
        unique_vessels=int(frame["mmsi"].nunique()),
        assessments=len(result.assessments),
        emitted_alerts=sum(alert.emitted for alert in result.alerts),
        near_misses=len(result.near_misses),
        maximum_risk_score=max(item.risk_score for item in result.assessments),
        scenarios=tuple(summaries),
    )
