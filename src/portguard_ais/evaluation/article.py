"""Tabular helpers for the SoftwareX reproducibility pack."""

from pathlib import Path

import pandas as pd

from portguard_ais.evaluation.benchmark import ArticleBenchmarkResult


def article_summary_frame(benchmark: ArticleBenchmarkResult) -> pd.DataFrame:
    """Return one manuscript-ready row per deterministic encounter scenario."""
    return pd.DataFrame(
        [
            {
                "scenario": item.name,
                "own_mmsi": item.own_mmsi,
                "target_mmsi": item.target_mmsi,
                "expected_encounter": item.expected_encounter,
                "colreg_context": item.expected_colreg_rule,
                "assessments": item.assessment_count,
                "converging_assessments": item.converging_assessments,
                "classification_consistency": item.classification_consistency,
                "peak_risk_score": item.peak_risk_score,
                "minimum_dcpa_nm": item.minimum_dcpa_nm,
                "minimum_converging_tcpa_min": item.minimum_converging_tcpa_min,
                "emitted_alerts": item.emitted_alerts,
                "first_emitted_state": item.first_emitted_state,
                "near_miss_detected": item.near_miss_detected,
            }
            for item in benchmark.scenarios
        ]
    )


def write_article_summary_csv(benchmark: ArticleBenchmarkResult, path: str | Path) -> Path:
    """Write the manuscript-ready scenario summary as CSV."""
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    article_summary_frame(benchmark).to_csv(output, index=False, encoding="utf-8")
    return output
