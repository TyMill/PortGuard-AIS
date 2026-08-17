"""Operational lead-time and computational-scaling evaluation for the JMSE study."""

import csv
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import perf_counter

from portguard_ais.assurance.pipeline import ResearchScenePipeline
from portguard_ais.evaluation.jmse_benchmark import JMSEBenchmarkResult, run_jmse_benchmark
from portguard_ais.evaluation.jmse_robustness import jitter_scenarios
from portguard_ais.evaluation.jmse_scenarios import jmse_scenarios
from portguard_ais.geometry.geodesy import EARTH_RADIUS_NM
from portguard_ais.models import VesselObservation


@dataclass(frozen=True)
class LeadTimeRow:
    """Per-seed operational timing summary for one method."""

    seed: int
    method: str
    hazard_scenarios: int
    detected_hazard_scenarios: int
    scenario_detection_rate: float
    mean_warning_lead_seconds: float
    median_warning_lead_seconds: float
    late_detection_rate: float


@dataclass(frozen=True)
class AssuranceDelayRow:
    """Difference between assured output and latent B4 hazard-state timing."""

    seed: int
    comparable_scenarios: int
    mean_assurance_delay_seconds: float
    max_assurance_delay_seconds: float


@dataclass(frozen=True)
class ScalingRow:
    """End-to-end runtime summary for one synthetic scene size."""

    vessel_count: int
    pairwise_encounters: int
    repeats: int
    mean_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    max_latency_ms: float
    missed_deadlines: int


_METHOD_FIELDS = {
    "B0_CPA_TCPA": "b0_cpa_tcpa",
    "B1_PAIRWISE_STATIC": "b1_pairwise_static",
    "B2_PAIRWISE_TEMPORAL": "b2_pairwise_temporal",
    "B3_SCENE_STATIC": "b3_scene_static",
    "B4_SCENE_TEMPORAL": "b4_scene_temporal",
    "OURS_ASSURED_OUTPUT": "ours_assured",
}


def _first_alert_steps(
    result: JMSEBenchmarkResult,
    field: str,
    *,
    pre_hazard_horizon_steps: int,
) -> dict[str, tuple[int, int | None]]:
    grouped: dict[str, list[object]] = {}
    for record in result.records:
        grouped.setdefault(record.scenario, []).append(record)

    output: dict[str, tuple[int, int | None]] = {}
    for scenario, records in grouped.items():
        hazardous = [record.step for record in records if record.expected_hazard]
        if not hazardous:
            continue
        onset = min(hazardous)
        end = max(hazardous)
        lower = max(0, onset - pre_hazard_horizon_steps)
        candidates = [
            record.step
            for record in records
            if lower <= record.step <= end and bool(getattr(record, field))
        ]
        output[scenario] = (onset, min(candidates) if candidates else None)
    return output


def summarize_lead_time(
    result: JMSEBenchmarkResult,
    *,
    seed: int,
    interval_seconds: int,
    pre_hazard_horizon_steps: int = 4,
) -> tuple[LeadTimeRow, ...]:
    """Summarize first actionable output relative to controlled hazard onset."""
    rows: list[LeadTimeRow] = []
    for method, field in _METHOD_FIELDS.items():
        timing = _first_alert_steps(
            result,
            field,
            pre_hazard_horizon_steps=pre_hazard_horizon_steps,
        )
        leads = [
            float((onset - first) * interval_seconds)
            for onset, first in timing.values()
            if first is not None
        ]
        detected = len(leads)
        hazard_count = len(timing)
        late = sum(value < 0.0 for value in leads)
        rows.append(
            LeadTimeRow(
                seed=seed,
                method=method,
                hazard_scenarios=hazard_count,
                detected_hazard_scenarios=detected,
                scenario_detection_rate=round(detected / hazard_count if hazard_count else 0.0, 6),
                mean_warning_lead_seconds=round(statistics.mean(leads), 6) if leads else float("nan"),
                median_warning_lead_seconds=(
                    round(statistics.median(leads), 6) if leads else float("nan")
                ),
                late_detection_rate=round(late / detected if detected else 0.0, 6),
            )
        )
    return tuple(rows)


def summarize_assurance_delay(
    result: JMSEBenchmarkResult,
    *,
    seed: int,
    interval_seconds: int,
    pre_hazard_horizon_steps: int = 4,
) -> AssuranceDelayRow:
    """Measure additional operator-action delay introduced by runtime assurance."""
    b4 = _first_alert_steps(
        result,
        "b4_scene_temporal",
        pre_hazard_horizon_steps=pre_hazard_horizon_steps,
    )
    ours = _first_alert_steps(
        result,
        "ours_assured",
        pre_hazard_horizon_steps=pre_hazard_horizon_steps,
    )
    delays: list[float] = []
    for scenario, (_, b4_first) in b4.items():
        ours_first = ours.get(scenario, (0, None))[1]
        if b4_first is None or ours_first is None:
            continue
        delays.append(float((ours_first - b4_first) * interval_seconds))
    return AssuranceDelayRow(
        seed=seed,
        comparable_scenarios=len(delays),
        mean_assurance_delay_seconds=(
            round(statistics.mean(delays), 6) if delays else float("nan")
        ),
        max_assurance_delay_seconds=max(delays) if delays else float("nan"),
    )


def run_lead_time_campaign(
    *,
    seed_count: int = 30,
    base_seed: int = 20260817,
    steps: int = 18,
    interval_seconds: int = 30,
    position_jitter_nm: float = 0.08,
) -> tuple[tuple[LeadTimeRow, ...], tuple[AssuranceDelayRow, ...]]:
    """Run lead-time evaluation across the same seeded geometry ensemble."""
    lead_rows: list[LeadTimeRow] = []
    delay_rows: list[AssuranceDelayRow] = []
    for offset in range(seed_count):
        seed = base_seed + offset
        scenarios = jitter_scenarios(
            jmse_scenarios(steps=steps, interval_seconds=interval_seconds, seed=seed),
            seed=seed,
            position_jitter_nm=position_jitter_nm,
        )
        result = run_jmse_benchmark(
            steps=steps,
            interval_seconds=interval_seconds,
            seed=seed,
            scenarios=scenarios,
        )
        lead_rows.extend(
            summarize_lead_time(
                result,
                seed=seed,
                interval_seconds=interval_seconds,
            )
        )
        delay_rows.append(
            summarize_assurance_delay(
                result,
                seed=seed,
                interval_seconds=interval_seconds,
            )
        )
    return tuple(lead_rows), tuple(delay_rows)


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    rank = (len(ordered) - 1) * percentile
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return ordered[low]
    fraction = rank - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def _radial_snapshot(vessel_count: int, timestamp: datetime) -> list[VesselObservation]:
    """Generate a dense synthetic scene with vessels directed toward a common center."""
    center_lat = 53.45
    center_lon = 14.60
    radius_nm = 1.5
    observations: list[VesselObservation] = []
    for index in range(vessel_count):
        angle = 2.0 * math.pi * index / vessel_count
        north_nm = radius_nm * math.cos(angle)
        east_nm = radius_nm * math.sin(angle)
        lat = center_lat + math.degrees(north_nm / EARTH_RADIUS_NM)
        cosine = max(abs(math.cos(math.radians(center_lat))), 1e-9)
        lon = center_lon + math.degrees(east_nm / (EARTH_RADIUS_NM * cosine))
        course = (math.degrees(angle) + 180.0) % 360.0
        observations.append(
            VesselObservation(
                timestamp=timestamp,
                mmsi=279000000 + index,
                lat=lat,
                lon=lon,
                sog=8.0,
                cog=course,
                heading=course,
                length_m=100.0,
                beam_m=18.0,
                position_accuracy_m=10.0,
                vessel_type="synthetic",
                source="jmse-scaling",
            )
        )
    return observations


def run_scaling_benchmark(
    *,
    vessel_counts: tuple[int, ...] = (2, 5, 10, 20, 40),
    repeats: int = 30,
    deadline_ms: float = 1000.0,
) -> tuple[ScalingRow, ...]:
    """Measure end-to-end scene-processing latency as vessel count increases."""
    if repeats < 2:
        raise ValueError("repeats must be at least 2")
    rows: list[ScalingRow] = []
    start = datetime(2026, 8, 17, 10, 0, tzinfo=UTC)
    for vessel_count in vessel_counts:
        if vessel_count < 2:
            raise ValueError("vessel counts must be at least 2")
        pipeline = ResearchScenePipeline()
        latencies: list[float] = []
        pairwise_encounters = 0
        for repeat in range(repeats):
            timestamp = start + timedelta(seconds=repeat * 30)
            snapshot = _radial_snapshot(vessel_count, timestamp)
            started = perf_counter()
            result = pipeline.process_snapshot(snapshot)
            latency_ms = (perf_counter() - started) * 1000.0
            latencies.append(latency_ms)
            pairwise_encounters = len(result.pairwise_assessments)
        rows.append(
            ScalingRow(
                vessel_count=vessel_count,
                pairwise_encounters=pairwise_encounters,
                repeats=repeats,
                mean_latency_ms=round(statistics.mean(latencies), 6),
                p95_latency_ms=round(_percentile(latencies, 0.95), 6),
                p99_latency_ms=round(_percentile(latencies, 0.99), 6),
                max_latency_ms=round(max(latencies), 6),
                missed_deadlines=sum(value > deadline_ms for value in latencies),
            )
        )
    return tuple(rows)


def write_operational_results(
    output_dir: str | Path,
    *,
    seed_count: int = 30,
    base_seed: int = 20260817,
    steps: int = 18,
    interval_seconds: int = 30,
    position_jitter_nm: float = 0.08,
    scaling_repeats: int = 30,
) -> None:
    """Write lead-time, assurance-delay, and scaling results to CSV files."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    lead_rows, delay_rows = run_lead_time_campaign(
        seed_count=seed_count,
        base_seed=base_seed,
        steps=steps,
        interval_seconds=interval_seconds,
        position_jitter_nm=position_jitter_nm,
    )
    scaling_rows = run_scaling_benchmark(repeats=scaling_repeats)

    datasets = (
        ("jmse_lead_time.csv", lead_rows),
        ("jmse_assurance_delay.csv", delay_rows),
        ("jmse_scaling.csv", scaling_rows),
    )
    for filename, rows in datasets:
        with (output / filename).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
            writer.writeheader()
            writer.writerows(asdict(row) for row in rows)
