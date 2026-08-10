"""Generate the complete deterministic SoftwareX reproducibility pack."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import Counter
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from portguard_ais.config import PortGuardConfig
from portguard_ais.evaluation.article import write_article_summary_csv
from portguard_ais.evaluation.benchmark import run_article_benchmark
from portguard_ais.evaluation.synthetic import ARTICLE_SCENARIOS, article_scenarios
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.reporting import write_html_report
from portguard_ais.serialization import export_bundle
from portguard_ais.visualization.article import plot_scenario_encounter
from portguard_ais.visualization.plots import plot_risk_timeline

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "article_run_v1"
INPUT_DIR = RUN_DIR / "input"
OUTPUT_DIR = RUN_DIR / "outputs"
FIGURE_DIR = RUN_DIR / "figures"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _environment_payload() -> dict[str, object]:
    return {
        "python": sys.version,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": {
            name: _package_version(name)
            for name in (
                "portguard-ais",
                "numpy",
                "pandas",
                "pydantic",
                "matplotlib",
            )
        },
    }


def _write_manifest(directory: Path) -> Path:
    manifest_path = directory / "manifest_sha256.json"
    files = sorted(
        path for path in directory.rglob("*") if path.is_file() and path != manifest_path
    )
    payload = {str(path.relative_to(directory)): _sha256(path) for path in files}
    _write_json(manifest_path, payload)
    return manifest_path


def main() -> None:
    for directory in (INPUT_DIR, OUTPUT_DIR, FIGURE_DIR):
        directory.mkdir(parents=True, exist_ok=True)

    steps = 12
    interval_seconds = 30
    frame = article_scenarios(steps=steps, interval_seconds=interval_seconds)
    input_csv = INPUT_DIR / "softwarex_article_scenarios.csv"
    frame.to_csv(input_csv, index=False)

    config = PortGuardConfig()
    result = PortGuardPipeline(config).process_frame(frame)
    benchmark = run_article_benchmark(steps=steps, interval_seconds=interval_seconds)

    bundle = export_bundle(
        result.assessments,
        result.alerts,
        result.near_misses,
        OUTPUT_DIR,
        trends=result.trends,
        hotspots=result.hotspots,
    )
    report = write_html_report(result, OUTPUT_DIR / "report.html")
    summary_csv = write_article_summary_csv(
        benchmark, OUTPUT_DIR / "softwarex_scenario_summary.csv"
    )

    figure_paths: dict[str, str] = {}
    for definition in ARTICLE_SCENARIOS:
        scenario_items = [
            item
            for item in result.assessments
            if item.own_mmsi == definition.own_mmsi and item.target_mmsi == definition.target_mmsi
        ]
        scenario_alerts = [
            alert
            for alert in result.alerts
            if scenario_items and alert.encounter_id == scenario_items[0].encounter_id
        ]
        geometry_path = plot_scenario_encounter(
            frame,
            result.assessments,
            definition.own_mmsi,
            definition.target_mmsi,
            FIGURE_DIR / f"{definition.name}_encounter.png",
            title=f"{definition.name.capitalize()} - {definition.expected_colreg_rule}",
        )
        figure_paths[f"{definition.name}_encounter"] = str(geometry_path.relative_to(ROOT))

        if definition.name == "head-on":
            timeline_path = plot_risk_timeline(
                scenario_items,
                FIGURE_DIR / "head_on_risk_timeline.png",
                alerts=scenario_alerts,
                thresholds=config.thresholds,
            )
            figure_paths["head_on_risk_timeline"] = str(timeline_path.relative_to(ROOT))

    encounter_counts = Counter(item.encounter_type.value for item in result.assessments)
    risk_counts = Counter(item.risk_level.value for item in result.assessments)
    alert_events = Counter(alert.event for alert in result.alerts)

    payload = {
        "software_version": "1.0.0",
        "run_design": {
            "steps": steps,
            "interval_seconds": interval_seconds,
            "scenario_count": len(ARTICLE_SCENARIOS),
            "scenario_names": [item.name for item in ARTICLE_SCENARIOS],
            "input_sha256": _sha256(input_csv),
        },
        "validation": result.validation.model_dump(mode="json"),
        "benchmark": benchmark.to_dict(),
        "encounter_type_counts": dict(sorted(encounter_counts.items())),
        "risk_level_counts": dict(sorted(risk_counts.items())),
        "alert_event_counts": dict(sorted(alert_events.items())),
        "generated_files": {
            **{key: str(value.relative_to(ROOT)) for key, value in bundle.items()},
            "html_report": str(report.relative_to(ROOT)),
            "scenario_summary_csv": str(summary_csv.relative_to(ROOT)),
            **figure_paths,
        },
    }
    environment_json = RUN_DIR / "environment.json"
    _write_json(environment_json, _environment_payload())
    payload["generated_files"]["environment"] = str(environment_json.relative_to(ROOT))

    summary_json = RUN_DIR / "softwarex_article_summary.json"
    _write_json(summary_json, payload)
    manifest = _write_manifest(RUN_DIR)

    assert result.validation.input_rows == 72
    assert result.validation.output_rows == 72
    assert result.validation.invalid_rows == 0
    assert benchmark.unique_vessels == 6
    assert benchmark.assessments == 36
    assert len(benchmark.scenarios) == 3
    assert all(item.converging_assessments > 0 for item in benchmark.scenarios)
    assert all(
        item.expected_type_count == item.converging_assessments for item in benchmark.scenarios
    )
    assert all(item.classification_consistency == 1.0 for item in benchmark.scenarios)
    assert all(item.near_miss_detected for item in benchmark.scenarios)
    assert all(Path(ROOT / path).is_file() for path in figure_paths.values())

    print("\n=== PortGuard-AIS 1.0.0 - SoftwareX article benchmark ===")
    print(f"Input rows:         {benchmark.input_rows}")
    print(f"Unique vessels:     {benchmark.unique_vessels}")
    print(f"Assessments:        {benchmark.assessments}")
    print(f"Emitted alerts:     {benchmark.emitted_alerts}")
    print(f"Near misses:        {benchmark.near_misses}")
    print(f"Maximum risk score: {benchmark.maximum_risk_score:.6f}")
    print("\nScenario results:")
    for item in benchmark.scenarios:
        print(
            f"  {item.name:11s} | {item.expected_colreg_rule:7s} | "
            f"{item.expected_encounter:19s} | consistency={item.classification_consistency:.3f} | "
            f"peak={item.peak_risk_score:.6f} | DCPA={item.minimum_dcpa_nm:.6f} NM | "
            f"alerts={item.emitted_alerts} | near-miss={item.near_miss_detected}"
        )
    print(f"\nSummary JSON: {summary_json.relative_to(ROOT)}")
    print(f"Summary CSV:  {summary_csv.relative_to(ROOT)}")
    print(f"Environment:  {environment_json.relative_to(ROOT)}")
    print(f"Manifest:     {manifest.relative_to(ROOT)}")
    print("All article assertions passed.")


if __name__ == "__main__":
    main()
