import json
from pathlib import Path

import pandas as pd
import pytest

from portguard_ais.evaluation.synthetic import synthetic_scenarios
from portguard_ais.pipeline import PortGuardPipeline
from portguard_ais.serialization import export_bundle


@pytest.mark.integration
def test_end_to_end_pipeline_and_export(tmp_path: Path) -> None:
    frame = synthetic_scenarios(steps=6)
    result = PortGuardPipeline().process_frame(frame)

    assert result.validation.output_rows == len(frame)
    assert result.assessments
    assert any(item.relative_motion.converging for item in result.assessments)
    paths = export_bundle(result.assessments, result.alerts, result.near_misses, tmp_path)
    assert all(path.is_file() for path in paths.values())
    exported = pd.read_csv(paths["assessments_csv"])
    assert "risk_score" in exported.columns
    geojson = json.loads(paths["assessments_geojson"].read_text(encoding="utf-8"))
    assert geojson["features"][0]["geometry"]["type"] == "LineString"
